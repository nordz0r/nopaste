from dataclasses import dataclass
from html import escape

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import TextLexer, guess_lexer
from pygments.util import ClassNotFound

HIGHLIGHT_STYLE = "nord-darker"
PLAIN_TEXT_LANGUAGE = "Plain text"

HTML_FORMATTER = HtmlFormatter(nowrap=True, style=HIGHLIGHT_STYLE)


@dataclass(frozen=True)
class HighlightedPaste:
    """Paste content rendered into syntax-highlighted, line-addressable HTML."""

    language: str
    lines: list[dict[str, int | str]]
    is_markdown: bool = False


def normalize_newlines(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def is_markdown_content(content: str, language: str) -> bool:
    lang_lower = language.lower()
    if "markdown" in lang_lower or lang_lower == "md":
        return True

    trimmed = content.strip()
    if not trimmed:
        return False

    lines = trimmed.splitlines()
    has_headers = any(line.startswith(("# ", "## ", "### ", "#### ")) for line in lines)
    has_code_fences = "```" in trimmed
    has_mermaid = "mermaid" in trimmed
    has_links = "[" in trimmed and "](" in trimmed
    has_lists = any(line.startswith(("- ", "* ", "1. ")) for line in lines)

    score = (has_headers * 2) + (has_code_fences * 2) + (has_mermaid * 3) + (has_links * 1) + (has_lists * 1)
    return score >= 2


def guess_paste_lexer(content: str) -> Lexer:
    if not content.strip():
        return TextLexer()

    try:
        return guess_lexer(content)
    except ClassNotFound:
        return TextLexer()


def get_lexer_display_name(lexer: Lexer) -> str:
    if isinstance(lexer, TextLexer) or getattr(lexer, "name", "") == "Text only":
        return PLAIN_TEXT_LANGUAGE
    return str(lexer.name)


def split_highlighted_lines(
    normalized_content: str, highlighted_html: str
) -> list[str] | None:
    if not normalized_content.endswith("\n") and highlighted_html.endswith("\n"):
        highlighted_html = highlighted_html[:-1]

    highlighted_lines = highlighted_html.split("\n")
    source_lines = normalized_content.split("\n")
    if len(highlighted_lines) != len(source_lines):
        return None

    return highlighted_lines


def build_plain_text_lines(normalized_content: str) -> list[str]:
    return [escape(line) for line in normalized_content.split("\n")]


def build_line_records(highlighted_lines: list[str]) -> list[dict[str, int | str]]:
    return [
        {
            "number": line_number,
            "anchor": f"L{line_number}",
            "html": line_html,
        }
        for line_number, line_html in enumerate(highlighted_lines, start=1)
    ]


def build_highlighted_paste(content: str) -> HighlightedPaste:
    normalized_content = normalize_newlines(content)
    lexer = guess_paste_lexer(normalized_content)
    highlighted_html = highlight(normalized_content, lexer, HTML_FORMATTER)
    highlighted_lines = split_highlighted_lines(normalized_content, highlighted_html)
    language = get_lexer_display_name(lexer)

    if highlighted_lines is None:
        highlighted_lines = build_plain_text_lines(normalized_content)
        language = PLAIN_TEXT_LANGUAGE

    is_md = is_markdown_content(normalized_content, language)

    return HighlightedPaste(
        language=language,
        lines=build_line_records(highlighted_lines),
        is_markdown=is_md,
    )
