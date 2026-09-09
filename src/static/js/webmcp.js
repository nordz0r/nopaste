/* Nopaste WebMCP tools.
 *
 * Registers read/create helpers so AI agents browsing the site (via
 * document.modelContext) can interact with pastes without scraping HTML.
 * Loaded after @mcp-b/global; safely no-ops if the polyfill is missing.
 */
(function () {
    "use strict";

    const MAX_TOOL_OUTPUT = 50000;
    const TRUNCATION_SUFFIX = "\n\n…[truncated]";

    function truncate(text) {
        if (typeof text !== "string") return String(text);
        if (text.length <= MAX_TOOL_OUTPUT) return text;
        return text.slice(0, MAX_TOOL_OUTPUT) + TRUNCATION_SUFFIX;
    }

    function ok(text) {
        return { content: [{ type: "text", text: truncate(text) }] };
    }

    function fail(message) {
        return {
            content: [{ type: "text", text: "Error: " + message }],
            isError: true,
        };
    }

    function json(value) {
        return ok(JSON.stringify(value, null, 2));
    }

    function isValidPasteId(id) {
        return typeof id === "string" && /^[A-Za-z0-9_-]{4,40}$/.test(id);
    }

    function readUserPastesCookie() {
        const match = document.cookie.match(/(?:^|;\s*)user_pastes=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function getCurrentPasteId() {
        const article = document.getElementById("instant-view-article");
        if (article && article.dataset && article.dataset.canonicalUrl) {
            const match = article.dataset.canonicalUrl.match(/\/paste\/([A-Za-z0-9_-]+)/);
            if (match) return match[1];
        }
        const pathMatch = window.location.pathname.match(/^\/paste\/([A-Za-z0-9_-]+)$/);
        return pathMatch ? pathMatch[1] : null;
    }

    function getCurrentPasteContent() {
        const field = document.getElementById("paste-raw-content");
        return field && typeof field.value === "string" ? field.value : null;
    }

    const tools = [
        {
            name: "get_paste",
            description:
                "Fetch the raw text of a Nopaste by its paste ID. Returns the plain-text body.",
            inputSchema: {
                type: "object",
                properties: {
                    paste_id: {
                        type: "string",
                        description: "The paste ID (4-40 chars, alphanumeric, dash or underscore).",
                    },
                },
                required: ["paste_id"],
            },
            async execute(args) {
                const id = args && args.paste_id;
                if (!isValidPasteId(id)) {
                    return fail("Invalid paste_id. Expected 4-40 chars, [A-Za-z0-9_-].");
                }
                try {
                    const res = await fetch("/raw/" + encodeURIComponent(id), {
                        headers: { Accept: "text/plain" },
                    });
                    if (res.status === 404) {
                        return fail("Paste not found: " + id);
                    }
                    if (!res.ok) {
                        return fail("HTTP " + res.status + " fetching paste " + id);
                    }
                    return ok(await res.text());
                } catch (err) {
                    return fail("Network error: " + (err && err.message ? err.message : err));
                }
            },
        },
        {
            name: "read_current_paste",
            description:
                "Read the paste currently open in the page. No arguments. Only works on /paste/<id> pages.",
            inputSchema: {
                type: "object",
                properties: {},
            },
            async execute() {
                const id = getCurrentPasteId();
                if (!id) {
                    return fail("No paste is currently open in this page.");
                }
                const content = getCurrentPasteContent();
                if (content === null) {
                    return fail(
                        "Could not read paste content from the page; the page is on a paste route but the source textarea is missing."
                    );
                }
                return json({
                    paste_id: id,
                    url: window.location.origin + "/paste/" + id,
                    content: content,
                });
            },
        },
        {
            name: "create_paste",
            description:
                "Create a new Nopaste from the provided text. Returns the paste URL and, when the server has a shortener configured, its short URL. Pass custom_slug to request a vanity short-link name: it is strict — if the slug is already taken or the shortener is unavailable, the paste is NOT created and an error is returned.",
            inputSchema: {
                type: "object",
                properties: {
                    content: {
                        type: "string",
                        description: "The text body of the paste.",
                    },
                    custom_slug: {
                        type: "string",
                        description:
                            "Optional custom short-link slug (letters, digits, underscore, dash; 5-64 chars). Strict: taken slug or shortener outage fails the call without creating the paste.",
                    },
                },
                required: ["content"],
            },
            async execute(args) {
                if (!args || typeof args.content !== "string" || !args.content.trim()) {
                    return fail("content must be a non-empty string.");
                }
                const body = new URLSearchParams();
                body.set("content", args.content);
                if (args.custom_slug) {
                    if (typeof args.custom_slug !== "string") {
                        return fail("custom_slug must be a string.");
                    }
                    body.set("custom_slug", args.custom_slug);
                }
                try {
                    const res = await fetch("/paste", {
                        method: "POST",
                        body: body,
                        headers: {
                            "Content-Type": "application/x-www-form-urlencoded",
                            Accept: "application/json",
                        },
                        redirect: "follow",
                    });
                    let payload = null;
                    try {
                        payload = await res.json();
                    } catch (parseErr) {
                        payload = null;
                    }
                    if (!res.ok || !payload || payload.status !== "ok") {
                        const detail =
                            payload && typeof payload.detail === "string"
                                ? payload.detail
                                : "HTTP " + res.status + " creating paste.";
                        return fail(detail);
                    }
                    return json({
                        paste_id: payload.paste_id,
                        url: payload.url,
                        short_url: payload.short_url,
                        share_url: payload.share_url,
                    });
                } catch (err) {
                    return fail("Network error: " + (err && err.message ? err.message : err));
                }
            },
        },
        {
            name: "list_recent_pastes",
            description:
                "List paste IDs from this browser's Nopaste history (the signed user_pastes cookie). Returns at most 50 IDs, most recent first.",
            inputSchema: {
                type: "object",
                properties: {},
            },
            async execute() {
                const cookie = readUserPastesCookie();
                if (!cookie) {
                    return json({ pastes: [], note: "No user_pastes cookie present." });
                }
                const dot = cookie.indexOf(".");
                const payload = dot >= 0 ? cookie.slice(0, dot) : cookie;
                let ids = [];
                try {
                    const padding = "=".repeat((-payload.length) % 4);
                    const decoded = atob(
                        payload.replace(/-/g, "+").replace(/_/g, "/") + padding
                    );
                    const parsed = JSON.parse(decoded);
                    if (Array.isArray(parsed)) ids = parsed.filter(isValidPasteId);
                } catch (err) {
                    return json({
                        pastes: [],
                        note: "Cookie present but payload could not be parsed client-side (it is server-signed).",
                    });
                }
                return json({ pastes: ids.slice(0, 50) });
            },
        },
    ];

    function register() {
        const ctx = document.modelContext;
        if (!ctx || typeof ctx.registerTool !== "function") return;
        for (const tool of tools) {
            try {
                ctx.registerTool(tool);
            } catch (err) {
                console.warn("Failed to register WebMCP tool", tool.name, err);
            }
        }
    }

    if (document.modelContext && typeof document.modelContext.registerTool === "function") {
        register();
    } else {
        window.addEventListener("load", register, { once: true });
    }
})();
