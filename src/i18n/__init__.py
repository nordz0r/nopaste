from __future__ import annotations

from typing import Any

from i18n import messages_en, messages_ru

_CATALOGS = {
    "en": messages_en.MESSAGES,
    "ru": messages_ru.MESSAGES,
}


def resolve_lang(
    accept_language: str | None = None, navigator_language: str | None = None
) -> str:
    """Return 'en' if primary language is English, otherwise 'ru' (status-quo default)."""
    candidates: list[str] = []
    if navigator_language:
        candidates.append(navigator_language)
    if accept_language:
        # e.g. "en-US,en;q=0.9,ru;q=0.8"
        for part in accept_language.split(","):
            tag = part.split(";")[0].strip()
            if tag:
                candidates.append(tag)
    for tag in candidates:
        primary = tag.lower().replace("_", "-").split("-", 1)[0]
        if primary == "en":
            return "en"
        if primary == "ru":
            return "ru"
    return "ru"


def t(key: str, lang: str = "ru", **kwargs: Any) -> str:
    catalog = _CATALOGS.get(lang) or _CATALOGS["ru"]
    fallback = _CATALOGS["en"]
    template = catalog.get(key) or fallback.get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template


def client_bundle(lang: str) -> dict[str, str]:
    """Subset of messages exposed to browser JS."""
    keys = [
        "toast.copied",
        "toast.copy_error",
        "toast.link_copied",
        "toast.content_copied",
        "toast.link_updated",
        "toast.slug_error",
        "toast.slug_taken",
        "toast.network_error",
        "toast.empty_paste",
        "toast.line_link_copied",
        "toast.code_copied",
        "paste.copy_code",
        "paste.favorite",
        "nav.login",
        "nav.logout",
        "toast.favorite_added",
        "toast.favorite_removed",
        "toast.auth_required",
        "toast.imported",
        "list.bookmarks",
        "list.created",
        "list.import_history",
    ]
    return {k: t(k, lang) for k in keys}
