import json
import re
from dataclasses import dataclass
from html import escape

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import JsonLexer, TextLexer, guess_lexer
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


CODE_LINE_PATTERNS = (
    re.compile(r"^\s*[\w.-]+\s*\([^)]*\)\s*\{"),
    re.compile(r"^\s*(?:def|class|function)\s+[\w$.-]+\b", re.IGNORECASE),
    re.compile(r"^\s*(?:return|case|esac|local|unset|export)\b", re.IGNORECASE),
    re.compile(
        r"^\s*(?:systemctl|docker|chmod|chown|sudo|npm|git|pip|curl|wget|apt|yum)\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:select|create\s+table|insert\s+into|update|alter\s+table|drop\s+table)\b",
        re.IGNORECASE,
    ),
)


def is_markdown_content(content: str, language: str) -> bool:
    lang_lower = (language or "").strip().lower()
    if "markdown" in lang_lower or lang_lower == "md":
        return True

    trimmed = content.strip()
    if not trimmed:
        return False

    lines = trimmed.splitlines()
    has_code_fences = any(line.lstrip().startswith("```") for line in lines)
    has_mermaid = any(line.strip().lower() == "mermaid" for line in lines)
    has_headers = any(re.match(r"^\s{0,3}#{1,6}\s+\S", line) for line in lines)
    has_links = any(re.search(r"\[[^\]]+\]\([^\)]+\)", line) for line in lines)
    has_lists = (
        sum(bool(re.match(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+\S", line)) for line in lines)
        >= 2
    )
    has_code_syntax = any(
        pattern.search(line) for line in lines for pattern in CODE_LINE_PATTERNS
    )

    if has_mermaid or has_code_fences:
        return True

    if has_code_syntax:
        return False

    if (
        has_headers
        or has_links
        or (has_lists and (has_headers or has_links or "`" in trimmed))
    ):
        return True

    if lang_lower in (PLAIN_TEXT_LANGUAGE.lower(), "text only", "text"):
        if has_lists or "`" in trimmed:
            return True

    return False


def guess_paste_lexer(content: str) -> Lexer:
    trimmed = content.strip()
    if not trimmed:
        return TextLexer()

    if (trimmed.startswith("{") and trimmed.endswith("}")) or (
        trimmed.startswith("[") and trimmed.endswith("]")
    ):
        try:
            json.loads(trimmed)
            return JsonLexer()
        except Exception:
            pass

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
    language = get_lexer_display_name(lexer)

    is_md = is_markdown_content(normalized_content, language)
    if is_md:
        language = "Markdown"
        try:
            from pygments.lexers import MarkdownLexer

            lexer = MarkdownLexer()
        except ClassNotFound:
            pass

    highlighted_html = highlight(normalized_content, lexer, HTML_FORMATTER)
    highlighted_lines = split_highlighted_lines(normalized_content, highlighted_html)

    if highlighted_lines is None:
        highlighted_lines = build_plain_text_lines(normalized_content)
        if not is_md:
            language = PLAIN_TEXT_LANGUAGE

    return HighlightedPaste(
        language=language,
        lines=build_line_records(highlighted_lines),
        is_markdown=is_md,
    )
