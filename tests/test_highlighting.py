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
