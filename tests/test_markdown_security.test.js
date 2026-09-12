const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const marked = require('../src/static/js/marked.min.js');

// Execute the actual template renderer, not a duplicate of its security rules.
const source = fs.readFileSync('src/templates/paste.html', 'utf8');
const start = source.indexOf('    const renderer = new marked.Renderer();');
const end = source.indexOf('    markdownContainer.addEventListener', start);
assert.ok(start > 0 && end > start);
const context = vm.createContext({ marked });
vm.runInContext(source.slice(start, end) + '\nmarked.setOptions({renderer, gfm: true});', context);

for (const input of [
    '# Test\n\n<script>alert(1)</script>',
    '# Test\n\n<img src=x onerror=alert(1)>',
    '[click](javascript:alert%281%29)',
    '[click](jav&#x61;script:alert%281%29)',
    '![click](data:image/svg+xml,test)',
    '```mermaid\n</pre><img src=x onerror=alert(1)>\n```',
]) {
    const html = marked.parse(input);
    assert.doesNotMatch(html, /<script|<img[^>]+onerror|(?:href|src)="(?:javascript|data):/i);
}
assert.match(marked.parse('**bold** [safe](https://example.com)'), /<strong>bold<\/strong>/);
assert.match(marked.parse('[safe](https://example.com)'), /href="https:\/\/example.com"/);
assert.match(marked.parse('```mermaid\ngraph TD; A-->B\n```'), /<pre class="mermaid">graph TD; A--&gt;B/);
console.log('Markdown security regression checks passed');
