// PR Lens diagrams in markdown pastes.
//
// Security model: the renderer output (an SVG string built from user JSON) is
// never inserted into the page DOM. It is wrapped in a Blob and shown through
// <img src="blob:...">, so the browser treats it as an image document: no
// scripts, no event handlers, no external loads. SMIL animation still plays.
// Everything else here is built with createElement/textContent only.
(function (root) {
    "use strict";

    const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));

    function needs(rawContent) {
        return /(^|\n)\s*```\s*prlens\b/i.test(rawContent)
            || /"kind"\s*:\s*"graph"/.test(rawContent) && /"schemaVersion"\s*:/.test(rawContent);
    }

    function isGraph(lang, codeText) {
        if (lang === "prlens") return true;
        if (lang !== "json") return false;
        try {
            const doc = JSON.parse(codeText);
            return Boolean(doc) && doc.kind === "graph" && typeof doc.schemaVersion === "string";
        } catch (_) {
            return false;
        }
    }

    // Placeholder markup emitted by the marked code renderer. The JSON source is
    // escaped into a hidden <textarea> (RCDATA), never into markup.
    function blockHtml(codeText) {
        return '<div class="prlens-wrap">'
            + '<div class="prlens-toolbar"><div class="prlens-tabs"></div></div>'
            + '<div class="prlens-stage" aria-live="polite"></div>'
            + `<textarea class="prlens-src" hidden readonly>${escapeHtml(codeText)}</textarea>`
            + "</div>";
    }

    function currentTheme(doc) {
        return doc.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    }

    // Renderer palette neutrals -> nopaste theme CSS variables. Diff colours
    // (added/modified/removed) stay as the renderer draws them.
    const PALETTE_VARS = {
        dark: {
            "#0d1117": "--bg-surface-alt", "#1c2128": "--bg-surface", "#3d444d": "--border",
            "#30363d": "--border", "#21262d": "--border", "#e6edf3": "--text-main",
            "#9198a1": "--text-muted", "#6e7681": "--accent",
        },
        light: {
            "#f4f5f7": "--bg-surface-alt", "#ffffff": "--bg-surface", "#d1d9e0": "--border",
            "#d8dee4": "--border", "#f1f3f5": "--bg-app", "#1f2328": "--text-main",
            "#59636e": "--text-muted", "#8c959f": "--accent",
        },
    };
    const SAFE_COLOR = /^(#[0-9a-f]{3,8}|rgba?\(\s*[\d.]+%?\s*,\s*[\d.]+%?\s*,\s*[\d.]+%?\s*(,\s*[\d.]+\s*)?\))$/i;

    // Only values that look like plain colours are used, and only colour
    // tokens in attribute/style positions are rewritten, never label text.
    function themeColors(doc, theme) {
        const map = PALETTE_VARS[theme] || {};
        const css = doc.defaultView && doc.defaultView.getComputedStyle
            ? doc.defaultView.getComputedStyle(doc.documentElement) : null;
        const out = {};
        if (!css) return out;
        Object.keys(map).forEach((hex) => {
            const value = String(css.getPropertyValue(map[hex]) || "").trim();
            if (SAFE_COLOR.test(value)) out[hex] = value;
        });
        return out;
    }

    function recolorSvg(svg, colors) {
        const keys = Object.keys(colors);
        if (!keys.length) return svg;
        const re = new RegExp(`(=["']|:\\s*)(${keys.join("|")})(?![0-9a-f])`, "gi");
        return svg.replace(re, (m, pre, hex) => pre + (colors[hex.toLowerCase()] || hex));
    }

    function slug(text) {
        return String(text || "diagram").toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "diagram";
    }

    function renderBlock(wrap, opts) {
        const doc = wrap.ownerDocument;
        const t = (key, fallback) => (opts.i18n && opts.i18n[key]) || fallback;
        const stage = wrap.querySelector(".prlens-stage");
        const tabs = wrap.querySelector(".prlens-tabs");
        const toolbar = wrap.querySelector(".prlens-toolbar");
        const src = wrap.querySelector(".prlens-src");
        const jsonText = src ? src.value : "";

        const showError = (message) => {
            const box = doc.createElement("div");
            box.className = "prlens-error";
            box.setAttribute("role", "alert");
            box.textContent = `${t("prlens.error", "PR Lens: could not render the diagram")}: ${message}`;
            stage.replaceChildren(box);
            const dl = toolbar.querySelector(".prlens-download");
            if (dl) dl.remove();
        };

        if (!root.NopastePrLens) {
            showError(t("prlens.unavailable", "renderer is not available"));
            return;
        }

        if (wrap._prlensUrl) URL.revokeObjectURL(wrap._prlensUrl);
        wrap._prlensUrl = null;

        let out;
        try {
            out = root.NopastePrLens.render(jsonText, wrap.dataset.lens || "", currentTheme(doc));
        } catch (err) {
            showError(err && err.message ? String(err.message).slice(0, 300) : "invalid graph.json");
            return;
        }
        wrap.dataset.lens = out.lens;

        const svg = recolorSvg(out.svg, themeColors(doc, currentTheme(doc)));
        const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
        wrap._prlensUrl = url;
        const img = doc.createElement("img");
        img.className = "prlens-img";
        img.decoding = "async";
        img.alt = `PR Lens: ${out.lens}`;
        img.src = url;
        stage.replaceChildren(img);

        if (!tabs.childElementCount && out.lenses.length > 1) {
            out.lenses.forEach((lens) => {
                const btn = doc.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-ghost prlens-tab";
                btn.textContent = lens;
                btn.dataset.lens = lens;
                btn.addEventListener("click", () => {
                    wrap.dataset.lens = lens;
                    renderBlock(wrap, opts);
                });
                tabs.appendChild(btn);
            });
        }
        tabs.querySelectorAll(".prlens-tab").forEach((btn) => {
            btn.classList.toggle("is-active", btn.dataset.lens === out.lens);
        });

        let dl = toolbar.querySelector(".prlens-download");
        if (!dl) {
            dl = doc.createElement("a");
            dl.className = "btn btn-ghost prlens-download";
            dl.textContent = t("prlens.download", "Download SVG");
            toolbar.appendChild(dl);
        }
        dl.href = url;
        let title = "diagram";
        try { title = JSON.parse(jsonText).id || title; } catch (_) { /* already rendered */ }
        dl.download = `${slug(title)}-${slug(out.lens)}-${currentTheme(doc)}.svg`;
    }

    function renderBlocks(container, opts) {
        const options = opts || {};
        const doc = container.ownerDocument;
        const wraps = () => container.querySelectorAll(".prlens-wrap");
        wraps().forEach((wrap) => renderBlock(wrap, options));
        if (!container._prlensThemeObserver && root.MutationObserver) {
            const observer = new root.MutationObserver(() => {
                wraps().forEach((wrap) => renderBlock(wrap, options));
            });
            observer.observe(doc.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
            container._prlensThemeObserver = observer;
        }
    }

    root.NopastePrLensView = { needs, isGraph, blockHtml, renderBlocks, recolorSvg };
})(typeof window !== "undefined" ? window : globalThis);
