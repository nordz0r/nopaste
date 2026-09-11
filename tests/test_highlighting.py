import highlighting as highlighting_module
from pygments.util import ClassNotFound


def test_highlighted_paste_handles_blank_content_as_plain_text():
    highlighted_paste = highlighting_module.build_highlighted_paste("   ")

    assert highlighted_paste.language == "Plain text"
    assert len(highlighted_paste.lines) == 1
    assert highlighted_paste.lines[0]["html"] == "   "


def test_highlighted_paste_handles_missing_lexer(monkeypatch):
    def raise_class_not_found(content):
        raise ClassNotFound("no lexer")

    monkeypatch.setattr(highlighting_module, "guess_lexer", raise_class_not_found)

    highlighted_paste = highlighting_module.build_highlighted_paste("alpha")

    assert highlighted_paste.language == "Plain text"
    assert highlighted_paste.lines[0]["html"] == "alpha"


def test_highlighted_paste_escapes_when_highlighter_line_count_does_not_match(
    monkeypatch,
):
    def return_mismatched_html(content, lexer, formatter):
        return "too\nmany\nlines"

    monkeypatch.setattr(highlighting_module, "highlight", return_mismatched_html)

    highlighted_paste = highlighting_module.build_highlighted_paste("<unsafe>")

    assert highlighted_paste.language == "Plain text"
    assert len(highlighted_paste.lines) == 1
    assert highlighted_paste.lines[0]["html"] == "&lt;unsafe&gt;"


def test_highlighted_paste_detects_markdown_content():
    md_content = (
        "# Title\n\n- Item 1\n- Item 2\n\n```mermaid\ngraph TD;\n    A-->B;\n```"
    )
    highlighted_paste = highlighting_module.build_highlighted_paste(md_content)

    assert highlighted_paste.is_markdown is True


def test_highlighted_paste_ignores_regular_code_for_markdown():
    python_code = "def hello():\n    print('world')\n"
    highlighted_paste = highlighting_module.build_highlighted_paste(python_code)

    assert highlighted_paste.is_markdown is False


def test_highlighted_paste_ignores_bash_script_with_comments_for_markdown():
    bash_code = (
        "# vpn-router: inet {REGION} → HTTP(S) proxy\n"
        "inet() {\n"
        "  local account='nord'\n"
        "  echo 'proxy'\n"
        "}\n"
    )
    highlighted_paste = highlighting_module.build_highlighted_paste(bash_code)

    assert highlighted_paste.is_markdown is False


def test_highlighted_paste_detects_markdown_with_backticks():
    md_content = (
        "# Title\n\nSome text with `inline code` and [link](http://example.com)"
    )
    highlighted_paste = highlighting_module.build_highlighted_paste(md_content)

    assert highlighted_paste.is_markdown is True
    assert highlighted_paste.language == "Markdown"


def test_highlighted_paste_detects_changelog_markdown_with_code_terms():
    changelog = """# Changelog

## v1.0.0

### Bug Fixes

- Update Docker publish pipeline
  ([`abc123`](https://github.com/example/project/commit/abc123))
- Improve Markdown detection for code and configs
"""

    highlighted_paste = highlighting_module.build_highlighted_paste(changelog)

    assert highlighted_paste.is_markdown is True
    assert highlighted_paste.language == "Markdown"


def test_highlighted_paste_detects_json_with_urls():
    json_content = """{
  "username": "demo-user",
  "gateway": {
    "http": "http://user:secret@proxy.example.com:8080"
  }
}"""
    highlighted_paste = highlighting_module.build_highlighted_paste(json_content)

    assert highlighted_paste.language == "JSON"
    assert highlighted_paste.is_markdown is False


def test_highlighted_paste_detects_yaml_not_markdown():
    yaml_content = """---
type: remap
inputs:
  - "trf-litellm-set-index-prod"
  - "trf-litellm-set-index-test"
source: |
  metadata = object(.metadata) ?? {}

  # Keep *_json payloads as strings, not structured objects.
  if exists(.messages_json) { .messages_json = to_string(.messages_json) ?? null }
"""
    highlighted_paste = highlighting_module.build_highlighted_paste(yaml_content)

    assert highlighted_paste.language == "YAML"
    assert highlighted_paste.is_markdown is False


def test_highlighted_paste_detects_yaml_without_doc_marker():
    yaml_content = """apiVersion: v1
kind: ConfigMap
metadata:
  name: demo
data:
  foo: bar
  list:
    - one
    - two
"""
    highlighted_paste = highlighting_module.build_highlighted_paste(yaml_content)

    assert highlighted_paste.language == "YAML"
    assert highlighted_paste.is_markdown is False


def test_highlighted_paste_keeps_markdown_with_yaml_front_matter():
    md_content = """---
title: Hello
date: 2024-01-01
---

# Title

Paragraph with [link](http://example.com)
"""
    highlighted_paste = highlighting_module.build_highlighted_paste(md_content)

    assert highlighted_paste.is_markdown is True
    assert highlighted_paste.language == "Markdown"


def test_highlighted_paste_detects_markdown_that_embeds_yaml_snippets():
    md_content = """# Telegram Instant View на том же URL

## Задача

Обычная ссылка пасты:

`https://paste.goldfinches.ru/paste/{paste_id}`

### `src/templates/paste.html`

```html
<article id="instant-view-article">
    <h1>Paste</h1>
</article>
```

Шаблон Instant View:

```text
~version: "2.1"

title: //article[@id="instant-view-article"]/h1
body: //article[@id="instant-view-article"]
site_name: "Nopaste"
description: //meta[@name="description"]/@content
```

## Проверка

- `CI: success`
- `Release: success`
"""
    highlighted_paste = highlighting_module.build_highlighted_paste(md_content)

    assert highlighted_paste.is_markdown is True
    assert highlighted_paste.language == "Markdown"


def test_markdown_instant_view_renderer_emits_safe_semantic_html():
    content = """# Telegram preview

This is **important** and [safe](https://example.com).

- one
- two

```python
<script>alert(1)</script>
```"""

    rendered = highlighting_module.render_markdown_for_instant_view(
        content, omit_first_heading=True
    )

    assert "<h1>Telegram preview</h1>" not in rendered
    assert (
        '<p>This is <strong>important</strong> and <a href="https://example.com">safe</a>.</p>'
        in rendered
    )
    assert "<ul><li>one</li><li>two</li></ul>" in rendered
    assert (
        '<pre data-language="python"><code>&lt;script&gt;alert(1)&lt;/script&gt;</code></pre>'
        in rendered
    )
    assert "<script>" not in rendered


def test_markdown_instant_view_renderer_rejects_unsafe_links():
    rendered = highlighting_module.render_markdown_for_instant_view(
        "[bad](javascript:alert(1)) [relative](/docs)"
    )

    assert "javascript:" not in rendered
    assert "bad" in rendered
    assert '<a href="/docs">relative</a>' in rendered


def test_extract_markdown_title_returns_plain_text():
    assert (
        highlighting_module.extract_markdown_title(
            "## **A** [safe](https://example.com)"
        )
        == "A safe"
    )
    assert highlighting_module.extract_markdown_title("plain text") == ""


def test_markdown_to_plain_text_removes_preview_syntax():
    assert (
        highlighting_module.markdown_to_plain_text(
            "# Title\n\n**Bold** [link](https://example.com)\n\n- item"
        )
        == "Title Bold link item"
    )


def test_highlighted_paste_keeps_unified_diff_not_yaml():
    diff_content = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
-old
+new
"""
    highlighted_paste = highlighting_module.build_highlighted_paste(diff_content)

    assert highlighted_paste.language == "Diff"
    assert highlighted_paste.is_markdown is False


# ---------------------------------------------------------------------------
# GFM Instant View renderer — new block-level features
# ---------------------------------------------------------------------------


def test_instant_view_renders_gfm_table():
    content = "| Name | Age |\n| ---- | --- |\n| Alice | 30 |\n| Bob | 25 |\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<table>" in rendered
    assert "<thead>" in rendered
    assert "<th>Name</th>" in rendered
    assert "<th>Age</th>" in rendered
    assert "<tbody>" in rendered
    assert "<td>Alice</td>" in rendered
    assert "<td>30</td>" in rendered
    assert "<td>Bob</td>" in rendered
    assert "<td>25</td>" in rendered


def test_instant_view_renders_table_without_leading_pipes():
    content = "Name | Score\n---- | -----\nAlice | 100\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<table>" in rendered
    assert "<th>Name</th>" in rendered
    assert "<td>Alice</td>" in rendered


def test_instant_view_renders_task_list_unchecked():
    content = "- [ ] Buy milk\n- [ ] Write tests\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert '<input type="checkbox" disabled>' in rendered
    assert "Buy milk" in rendered


def test_instant_view_renders_task_list_checked():
    content = "- [x] Done task\n- [X] Also done\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert 'checked=""' in rendered
    assert "Done task" in rendered


def test_instant_view_renders_mixed_task_and_plain_list():
    content = "- [ ] Todo\n- [x] Done\n- Plain item\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert '<input type="checkbox" disabled>' in rendered
    assert 'checked=""' in rendered
    assert "<li>Plain item</li>" in rendered


def test_instant_view_renders_thematic_break():
    content = "Above\n\n---\n\nBelow\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<hr>" in rendered
    assert "<p>Above</p>" in rendered
    assert "<p>Below</p>" in rendered


def test_instant_view_renders_thematic_break_asterisks():
    content = "Before\n\n***\n\nAfter\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<hr>" in rendered


def test_instant_view_renders_setext_heading_level1():
    content = "My Title\n========\n\nParagraph\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<h1>My Title</h1>" in rendered
    assert "<p>Paragraph</p>" in rendered


def test_instant_view_renders_setext_heading_level2():
    content = "Subtitle\n--------\n\nText\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<h2>Subtitle</h2>" in rendered


def test_instant_view_renders_autolink_url():
    content = "Visit <https://example.com> for info.\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert '<a href="https://example.com">https://example.com</a>' in rendered


def test_instant_view_renders_autolink_email():
    content = "Contact <user@example.com> please.\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert 'href="mailto:user@example.com"' in rendered
    assert "user@example.com" in rendered


def test_instant_view_rejects_autolink_javascript():
    # javascript: is not a valid autolink scheme per GFM.
    # The angle-bracket text is HTML-escaped; no clickable href is emitted.
    content = "Bad link: <javascript:alert(1)>\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert 'href="javascript:' not in rendered
    assert "<script" not in rendered
    assert "&lt;javascript:alert(1)&gt;" in rendered


def test_instant_view_table_parses_escaped_pipes():
    content = "| Name | Note |\n| --- | --- |\n| Alice | a \\| b |\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<td>a | b</td>" in rendered


def test_instant_view_table_does_not_swallow_malformed_prose_row():
    content = "Intro\nThis is prose\n| --- | --- |\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<table>" not in rendered
    assert "<p>Intro This is prose | --- | --- |</p>" in rendered


def test_instant_view_table_rejects_mismatched_header():
    rendered = highlighting_module.render_markdown_for_instant_view(
        "Name | Note | Extra\n--- | ---\n"
    )
    assert "<table>" not in rendered
    assert "Name | Note | Extra" in rendered


def test_instant_view_table_escaped_pipe_in_code_and_at_row_end():
    rendered = highlighting_module.render_markdown_for_instant_view(
        "Name | Note\n--- | ---\n`a\\|b` | end\\|\n"
    )
    assert "<td><code>a|b</code></td><td>end|</td>" in rendered


def test_instant_view_table_escapes_html_in_cells():
    content = "| Col |\n| --- |\n| <script>alert(1)</script> |\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_instant_view_strikethrough_in_inline():
    content = "This is ~~deleted~~ text.\n"
    rendered = highlighting_module.render_markdown_for_instant_view(content)
    assert "<del>deleted</del>" in rendered
