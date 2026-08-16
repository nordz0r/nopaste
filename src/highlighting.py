import json
import re
from dataclasses import dataclass
from html import escape

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import JsonLexer, MarkdownLexer, TextLexer, YamlLexer, guess_lexer
from pygments.util import ClassNotFound

HIGHLIGHT_STYLE = "nord-darker"
PLAIN_TEXT_LANGUAGE = "Plain text"
YAML_LANGUAGES = frozenset({"yaml", "yml"})

HTML_FORMATTER = HtmlFormatter(nowrap=True, style=HIGHLIGHT_STYLE)

# YAML document start / end markers (allow trailing spaces from pasted configs).
YAML_DOC_START = re.compile(r"^---\s*$")
YAML_DOC_MARKER = re.compile(r"^(---|\.\.\.)\s*$")
# Mapping key: name: / dotted.names: / "quoted":
YAML_KEY_LINE = re.compile(
    r'^\s*(?:[A-Za-z_][\w./-]*|"(?:\\.|[^"\\])+"|\'(?:\\.|[^\'\\])+\')\s*:'
    r"(?:\s*$|\s+[|>][+-]?\d*\s*$|\s+.+)"
)
YAML_BLOCK_SCALAR = re.compile(
    r'^\s*(?:[A-Za-z_][\w./-]*|"(?:\\.|[^"\\])+"|\'(?:\\.|[^\'\\])+\')\s*:\s*[|>][+-]?\d*\s*$'
)
YAML_LIST_ITEM = re.compile(r"^\s*-\s+\S")


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


MARKDOWN_HEADER = re.compile(r"^\s{0,3}#{1,6}\s+\S")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\([^\)]+\)")
MARKDOWN_LIST_ITEM = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+\S")
UNIFIED_DIFF_FILE_HEADER = re.compile(r"^---\s+\S")


def _non_empty_lines(content: str) -> list[str]:
    return [line for line in content.splitlines() if line.strip()]


def _is_json_envelope(trimmed: str) -> bool:
    return (trimmed.startswith("{") and trimmed.endswith("}")) or (
        trimmed.startswith("[") and trimmed.endswith("]")
    )


def _is_unified_diff_header(first_line: str) -> bool:
    return bool(
        UNIFIED_DIFF_FILE_HEADER.match(first_line) or first_line.startswith("+++ ")
    )


def _count_yaml_signals(sample: list[str]) -> tuple[int, int, int, bool]:
    key_lines = 0
    list_items = 0
    block_scalars = 0
    has_doc_start = bool(YAML_DOC_START.match(sample[0]))

    for line in sample:
        if line.lstrip().startswith("#"):
            continue
        if YAML_BLOCK_SCALAR.match(line):
            block_scalars += 1
        if YAML_KEY_LINE.match(line):
            key_lines += 1
        if YAML_LIST_ITEM.match(line):
            list_items += 1

    return key_lines, list_items, block_scalars, has_doc_start


def _matches_yaml_signal_threshold(
    key_lines: int, list_items: int, block_scalars: int, has_doc_start: bool
) -> bool:
    return (
        (has_doc_start and key_lines >= 2)
        or (block_scalars >= 1 and key_lines >= 2)
        or (key_lines >= 3 and list_items >= 1)
        or key_lines >= 4
    )


def looks_like_yaml(content: str) -> bool:
    """Heuristic YAML detection for configs that Pygments often mislabels (Diff/Text)."""
    trimmed = content.strip()
    if not trimmed or _is_json_envelope(trimmed):
        return False

    # Unified diffs start with "--- a/..." / "+++ b/...", not a bare document marker.
    if _is_unified_diff_header(trimmed.splitlines()[0]):
        return False

    sample = _non_empty_lines(trimmed)[:100]
    if not sample:
        return False

    return _matches_yaml_signal_threshold(*_count_yaml_signals(sample))


def _markdown_body_signals(body_lines: list[str]) -> bool:
    has_headers = any(MARKDOWN_HEADER.match(line) for line in body_lines)
    has_fences = any(line.lstrip().startswith("```") for line in body_lines)
    has_links = any(MARKDOWN_LINK.search(line) for line in body_lines)
    return has_headers or has_fences or has_links


def has_markdown_after_yaml_front_matter(content: str) -> bool:
    """Detect Markdown documents that begin with YAML front matter."""
    lines = normalize_newlines(content).splitlines()
    if not lines or not YAML_DOC_START.match(lines[0]):
        return False

    close_idx = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if YAML_DOC_MARKER.match(line)
        ),
        None,
    )
    if close_idx is None:
        return False

    body_lines = lines[close_idx + 1 :]
    if not "\n".join(body_lines).strip():
        return False

    return _markdown_body_signals(body_lines)


def _has_code_syntax(lines: list[str]) -> bool:
    return any(pattern.search(line) for line in lines for pattern in CODE_LINE_PATTERNS)


def _markdown_feature_flags(lines: list[str]) -> tuple[bool, bool, bool, bool, bool]:
    has_code_fences = any(line.lstrip().startswith("```") for line in lines)
    has_mermaid = any(line.strip().lower() == "mermaid" for line in lines)
    has_headers = any(MARKDOWN_HEADER.match(line) for line in lines)
    has_links = any(MARKDOWN_LINK.search(line) for line in lines)
    has_lists = sum(bool(MARKDOWN_LIST_ITEM.match(line)) for line in lines) >= 2
    return has_code_fences, has_mermaid, has_headers, has_links, has_lists


def _has_dominant_markdown_signals(content: str) -> bool:
    """Prefer Markdown when a YAML-like paste is actually a Markdown document.

    YAML configs share `# comments` and `- list` items with Markdown, but they
    almost never use ATX headings of level 2+, fenced code blocks, or
    `[text](url)` links. Those signals mean the YAML-looking `key: value`
    lines are examples embedded in a Markdown note.
    """
    lines = content.splitlines()
    has_code_fences, has_mermaid, has_headers, has_links, _has_lists = (
        _markdown_feature_flags(lines)
    )
    has_heading_level_2_plus = any(re.match(r"^#{2,6}\s+\S", line) for line in lines)
    return (
        has_code_fences
        or has_mermaid
        or has_heading_level_2_plus
        or (has_headers and has_links)
    )


def is_markdown_content(content: str, language: str) -> bool:
    lang_lower = (language or "").strip().lower()
    if "markdown" in lang_lower or lang_lower == "md":
        return True

    trimmed = content.strip()
    if not trimmed:
        return False

    # YAML configs often contain "# comments" and "- list" items that look like Markdown.
    # Treat YAML-like pastes as Markdown when they have front matter + a Markdown
    # body, or when Markdown structure clearly dominates embedded YAML snippets.
    if lang_lower in YAML_LANGUAGES or looks_like_yaml(trimmed):
        return has_markdown_after_yaml_front_matter(
            trimmed
        ) or _has_dominant_markdown_signals(trimmed)

    lines = trimmed.splitlines()
    has_code_fences, has_mermaid, has_headers, has_links, has_lists = (
        _markdown_feature_flags(lines)
    )

    if has_mermaid or has_code_fences:
        return True
    if _has_code_syntax(lines):
        return False
    if has_headers or has_links or (has_lists and "`" in trimmed):
        return True
    if lang_lower in (PLAIN_TEXT_LANGUAGE.lower(), "text only", "text"):
        return has_lists or "`" in trimmed
    return False


def guess_paste_lexer(content: str) -> Lexer:
    trimmed = content.strip()
    if not trimmed:
        return TextLexer()

    if _is_json_envelope(trimmed):
        try:
            json.loads(trimmed)
            return JsonLexer()
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Prefer YAML before Pygments: document markers like "---" are often labeled Diff.
    if looks_like_yaml(trimmed):
        return YamlLexer()

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
        lexer = MarkdownLexer()

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
