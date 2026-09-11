// tests/test_webmcp.test.js
// Unit tests for WebMCP create_paste tool logic in Node.js test runner.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function loadWebMcp(mockFetch) {
    const code = fs.readFileSync(
        path.join(__dirname, "..", "src", "static", "js", "webmcp.js"),
        "utf8"
    );
    const registered = [];
    const context = {
        document: {
            modelContext: {
                registerTool: (tool) => registered.push(tool),
            },
            getElementById: () => null,
            cookie: "",
        },
        window: {
            location: {
                pathname: "/",
                origin: "https://example.test",
            },
            addEventListener: () => {},
        },
        console,
        URLSearchParams,
        fetch: mockFetch,
    };
    vm.runInNewContext(code, context);
    return registered.find((t) => t.name === "create_paste");
}

test("create_paste sends Accept: application/json and returns short_url on 201", async () => {
    let capturedHeaders = null;
    let capturedBody = null;
    const tool = loadWebMcp(async (url, init) => {
        capturedHeaders = init.headers;
        capturedBody = init.body.toString();
        return {
            ok: true,
            status: 201,
            json: async () => ({
                status: "ok",
                paste_id: "AbCd1234",
                url: "https://example.test/paste/AbCd1234",
                short_url: "https://gldf.ru/my-slug",
                share_url: "https://gldf.ru/my-slug",
            }),
        };
    });

    const result = await tool.execute({
        content: "hello from test",
        custom_slug: "my-slug",
    });

    assert.equal(result.isError, undefined);
    assert.equal(capturedHeaders.Accept, "application/json");
    assert.match(capturedBody, /content=hello\+from\+test/);
    assert.match(capturedBody, /custom_slug=my-slug/);

    const parsed = JSON.parse(result.content[0].text);
    assert.equal(parsed.paste_id, "AbCd1234");
    assert.equal(parsed.short_url, "https://gldf.ru/my-slug");
    assert.equal(parsed.share_url, "https://gldf.ru/my-slug");
});

test("create_paste propagates server error detail on 409 slug_taken", async () => {
    const tool = loadWebMcp(async () => ({
        ok: false,
        status: 409,
        json: async () => ({
            detail: "This short link name is already in use.",
        }),
    }));

    const result = await tool.execute({
        content: "hello",
        custom_slug: "taken-slug",
    });

    assert.equal(result.isError, true);
    assert.match(
        result.content[0].text,
        /Error: This short link name is already in use\./
    );
});

test("create_paste fails early for empty content without calling network", async () => {
    let called = false;
    const tool = loadWebMcp(async () => {
        called = true;
    });

    const result = await tool.execute({ content: "   " });
    assert.equal(result.isError, true);
    assert.equal(called, false);
});

test("app layout loads WebMCP polyfill before webmcp.js", () => {
    const html = fs.readFileSync(
        path.join(__dirname, "..", "src", "templates", "layouts", "app.html"),
        "utf8"
    );
    const polyfillIndex = html.indexOf("@mcp-b/global");
    const webmcpIndex = html.indexOf("/static/js/webmcp.js");
    assert.notEqual(polyfillIndex, -1, "polyfill script missing from app.html");
    assert.notEqual(webmcpIndex, -1, "webmcp.js script missing from app.html");
    assert.ok(
        polyfillIndex < webmcpIndex,
        "Expected @mcp-b/global to load before webmcp.js so document.modelContext exists"
    );
});

test("registers all tools immediately when document.modelContext is present", () => {
    const code = fs.readFileSync(
        path.join(__dirname, "..", "src", "static", "js", "webmcp.js"),
        "utf8"
    );
    const registered = [];
    let listenerAdded = false;
    const context = {
        document: {
            modelContext: {
                registerTool: (tool) => registered.push(tool),
            },
            getElementById: () => null,
            cookie: "",
        },
        window: {
            location: {
                pathname: "/",
                origin: "https://example.test",
            },
            addEventListener: () => {
                listenerAdded = true;
            },
        },
        console,
        URLSearchParams,
        fetch: async () => ({}),
    };
    vm.runInNewContext(code, context);

    assert.equal(listenerAdded, false);
    const names = registered.map((t) => t.name);
    assert.deepEqual(names, [
        "get_paste",
        "read_current_paste",
        "create_paste",
        "list_recent_pastes",
    ]);
});

test("registers all tools on window load when document.modelContext is deferred", () => {
    const code = fs.readFileSync(
        path.join(__dirname, "..", "src", "static", "js", "webmcp.js"),
        "utf8"
    );
    const registered = [];
    let loadHandler = null;
    const doc = {
        getElementById: () => null,
        cookie: "",
    };
    const context = {
        document: doc,
        window: {
            location: {
                pathname: "/",
                origin: "https://example.test",
            },
            addEventListener: (event, handler) => {
                if (event === "load") {
                    loadHandler = handler;
                }
            },
        },
        console,
        URLSearchParams,
        fetch: async () => ({}),
    };
    vm.runInNewContext(code, context);

    assert.equal(registered.length, 0);
    assert.equal(typeof loadHandler, "function");

    doc.modelContext = {
        registerTool: (tool) => registered.push(tool),
    };
    loadHandler();

    const names = registered.map((t) => t.name);
    assert.deepEqual(names, [
        "get_paste",
        "read_current_paste",
        "create_paste",
        "list_recent_pastes",
    ]);
});
