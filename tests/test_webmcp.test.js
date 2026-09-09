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
