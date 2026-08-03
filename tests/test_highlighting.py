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
    md_content = "# Title\n\n- Item 1\n- Item 2\n\n```mermaid\ngraph TD;\n    A-->B;\n```"
    highlighted_paste = highlighting_module.build_highlighted_paste(md_content)

    assert highlighted_paste.is_markdown is True


def test_highlighted_paste_ignores_regular_code_for_markdown():
    python_code = "def hello():\n    print('world')\n"
    highlighted_paste = highlighting_module.build_highlighted_paste(python_code)

    assert highlighted_paste.is_markdown is False
