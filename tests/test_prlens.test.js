const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const test = require('node:test');
const marked = require('../src/static/js/marked.min.js');

const viewSource = fs.readFileSync('src/static/js/prlens-view.js', 'utf8');

function loadView(extra = {}) {
    const ctx = vm.createContext({ ...extra });
    ctx.window = ctx;
    vm.runInContext(viewSource, ctx);
    return ctx;
}

function loadPasteRenderer(prlensView) {
    const source = fs.readFileSync('src/templates/paste.html', 'utf8');
    const start = source.indexOf('    const renderer = new marked.Renderer();');
    const end = source.indexOf('    markdownContainer.addEventListener', start);
    assert.ok(start > 0 && end > start);
    const context = vm.createContext({ marked, prlensView });
    vm.runInContext(source.slice(start, end) + '\nmarked.setOptions({renderer, gfm: true});', context);
    return context;
}

const graph = {
    schemaVersion: '0.2.0', kind: 'graph', id: 'xss', title: 'x', summary: 'x',
    lenses: ['architecture'],
};
const payloads = [
    '</textarea><img src=x onerror=alert(1)>',
    '<script>alert(1)</script>',
    '"><svg onload=alert(1)>',
];

test('graph detection', () => {
    const { NopastePrLensView: v } = loadView();
    assert.equal(v.needs('```prlens\n{}\n```'), true);
    assert.equal(v.needs('```json\n{"schemaVersion":"0.2.0","kind":"graph"}\n```'), true);
    assert.equal(v.needs('```json\n{"a":1}\n```'), false);
    assert.equal(v.isGraph('prlens', 'not json'), true);
    assert.equal(v.isGraph('json', JSON.stringify(graph)), true);
    assert.equal(v.isGraph('json', '{"kind":"graph"}'), false);
    assert.equal(v.isGraph('js', JSON.stringify(graph)), false);
});

test('XSS payloads in graph.json stay escaped text in markdown output', () => {
    const { NopastePrLensView: v } = loadView();
    loadPasteRenderer(v);
    for (const payload of payloads) {
        const doc = { ...graph, title: payload, summary: payload };
        for (const lang of ['prlens', 'json']) {
            const html = marked.parse('```' + lang + '\n' + JSON.stringify(doc) + '\n```');
            assert.match(html, /class="prlens-wrap"/);
            assert.doesNotMatch(html, /<script|<img|<svg/i, `${lang}: ${payload}`);
            // exactly one textarea, and its body cannot close it early
            assert.equal((html.match(/<\/textarea>/g) || []).length, 1);
        }
    }
    // Non-graph json blocks render as ordinary code.
    assert.doesNotMatch(marked.parse('```json\n{"a":1}\n```'), /prlens-wrap/);
});

test('view never injects renderer output as markup', () => {
    // The SVG may only reach the page as an image (blob: URL on <img>).
    assert.doesNotMatch(viewSource, /innerHTML|outerHTML|insertAdjacentHTML|document\.write|DOMParser|createContextualFragment/);
    assert.match(viewSource, /new Blob\(\[svg\], \{ type: "image\/svg\+xml" \}\)/);
    assert.match(viewSource, /img\.src = url/);
});

test('npm dependencies are pinned to exact versions', () => {
    const pkg = JSON.parse(fs.readFileSync('frontend/prlens/package.json', 'utf8'));
    for (const deps of [pkg.dependencies, pkg.devDependencies]) {
        for (const [name, version] of Object.entries(deps)) {
            assert.match(version, /^\d+\.\d+\.\d+$/, `${name} must be pinned`);
        }
    }
    const dockerfile = fs.readFileSync('Dockerfile', 'utf8');
    assert.match(dockerfile, /npm ci/);
    assert.match(dockerfile, /prlens\.min\.js/);
});

// Runs only when the bundle has been built (Docker image / local `npm run build`).
const bundlePath = path.join('src', 'static', 'js', 'prlens.min.js');
test('bundle renders a real graph and keeps labels escaped', { skip: !fs.existsSync(bundlePath) }, () => {
    const ctx = vm.createContext({});
    ctx.window = ctx;
    vm.runInContext(fs.readFileSync(bundlePath, 'utf8'), ctx);
    const doc = JSON.parse(fs.readFileSync('tests/fixtures/prlens-graph.json', 'utf8'));
    doc.nodes[0].label = payloads[1];
    for (const theme of ['dark', 'light']) {
        const out = ctx.NopastePrLens.render(JSON.stringify(doc), 'unknown-lens', theme);
        assert.equal(out.lens, 'architecture');
        assert.match(out.svg, /^<svg /);
        assert.doesNotMatch(out.svg, /<script|<foreignObject|\son\w+=/i);
        assert.match(out.svg, /&lt;script&gt;/);
    }
    assert.throws(() => ctx.NopastePrLens.render('{not json', '', 'dark'), /not valid JSON/);
    assert.throws(() => ctx.NopastePrLens.render('{"kind":"graph"}', '', 'dark'), /does not match PR Lens schema/);
});

test('recolorSvg maps palette colours in attributes only, not label text', () => {
    const view = loadView().NopastePrLensView;
    const out = view.recolorSvg(
        '<rect fill="#0d1117" style="stroke:#3D444D"/><text>#0d1117</text>',
        { '#0d1117': '#212427', '#3d444d': '#33373b' },
    );
    assert.equal(out, '<rect fill="#212427" style="stroke:#33373b"/><text>#0d1117</text>');
});
