import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from database import Database, create_database_from_settings
from highlighting import build_highlighted_paste
from i18n import client_bundle, resolve_lang, t as i18n_t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHORT_PASTE_ID_LENGTH = 6
SHORT_PASTE_ID_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
MAX_PASTE_ID_GENERATION_ATTEMPTS = 20
APP_NAME = "Nopaste"
DEFAULT_META_DESCRIPTION = "Share text, logs, notes, and configs with Nopaste."
BRAND_PREVIEW_IMAGE_PATH = "images/goldfinches_logo.png"
APP_VERSION_ENV_VAR = "APP_VERSION"

app = FastAPI(
    title=APP_NAME,
    description="API для простого nopaste приложения",
    debug=settings.DEBUG,
)


class SlugTakenError(Exception):
    """Raised when Shlink rejects a custom slug as already taken."""


def request_lang(request: Request) -> str:
    return resolve_lang(accept_language=request.headers.get("accept-language"))


def template_context(request: Request, **extra: Any) -> dict[str, Any]:
    lang = request_lang(request)
    ctx: dict[str, Any] = {
        "request": request,
        "base_template": get_design_base_template(),
        "design_name": get_active_design_name(),
        "lang": lang,
        "t": lambda key, **kwargs: i18n_t(key, lang, **kwargs),
        "i18n_js": client_bundle(lang),
        "shrink_enabled": settings.shrink_enabled,
    }
    ctx.update(extra)
    return ctx


# Кастомный класс для добавления заголовков кэширования
class CacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000"
        return response


db = create_database_from_settings(settings)
logger.info("Paste storage backend: %s", db.backend_name)

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static", CacheStaticFiles(directory=str(BASE_DIR / "static")), name="static"
)


def _is_ip_in_allowlist(ip: str, allowlist: list[str]) -> bool:
    """Return True if ip matches any entry in allowlist (CIDR or IP).
    Empty allowlist → allow everyone.
    """
    if not allowlist:
        return True
    from ipaddress import ip_address, ip_network

    # Normalize special test client values to localhost
    norm = (ip or "").strip().lower()
    if norm in {"testclient", "testserver", "localhost"}:
        norm = "127.0.0.1"

    try:
        client_ip = ip_address(norm)
    except Exception:
        return False

    for entry in allowlist:
        try:
            if client_ip in ip_network(entry.strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


@app.middleware("http")
async def restrict_api_docs(request: Request, call_next):
    """Restrict access to FastAPI automatic documentation endpoints based on DOCS_ALLOWLIST.

    Used in production (see docs_allowlist in Ansible deployment).
    """
    if request.url.path in {"/docs", "/redoc", "/openapi.json"}:
        # Collect possible real client IPs (TestClient, proxies, etc.)
        candidates: list[str] = []
        if request.client and request.client.host:
            candidates.append(request.client.host)
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            candidates.append(fwd.split(",")[0].strip())
        # TestClient often reports as "testclient"
        candidates.append("127.0.0.1")

        for candidate in candidates:
            if _is_ip_in_allowlist(candidate, settings.DOCS_ALLOWLIST):
                break
        else:
            # none of the candidates were allowed
            return PlainTextResponse("Forbidden", status_code=403)

    return await call_next(request)


@app.middleware("http")
async def add_noindex_header(request: Request, call_next):
    """Add X-Robots-Tag header to prevent search engine indexing."""
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def load_version_from_pyproject(pyproject_path: Path) -> str | None:
    try:
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None

    version = pyproject_data.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        return None
    return version.strip()


def load_version_from_environment() -> str | None:
    version = os.getenv(APP_VERSION_ENV_VAR, "").strip()
    return version or None


def iter_version_candidate_paths() -> list[Path]:
    return [
        PROJECT_ROOT / "pyproject.toml",
        BASE_DIR / "pyproject.toml",
    ]


def load_asset_version() -> str:
    env_version = load_version_from_environment()
    if env_version:
        return env_version

    seen_paths: set[Path] = set()

    for version_path in iter_version_candidate_paths():
        if version_path in seen_paths:
            continue
        seen_paths.add(version_path)
        version = load_version_from_pyproject(version_path)

        if version:
            return version

    logger.warning(
        "Could not load app version from known paths: %s",
        ", ".join(str(path) for path in seen_paths),
    )
    return "dev"


def current_year() -> int:
    return datetime.now().year


def get_active_design_name() -> str:
    """Return the active UI design name (sanitized, never empty)."""
    design = (settings.UI_DESIGN or "default").strip() or "default"
    return design


def get_design_base_template() -> str:
    """Resolve the active pluggable design base template path.

    Designs are stored under templates/designs/<name>/base.html .
    Controlled by settings.UI_DESIGN (defaults to "default").
    """
    return f"designs/{get_active_design_name()}/base.html"


def get_shrink_base_url() -> str:
    if settings.SHRINK_URL:
        return settings.SHRINK_URL.rstrip("/")
    return "https://gldf.ru"


APP_VERSION = load_asset_version()
templates.env.globals["asset_version"] = APP_VERSION
templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["current_year"] = current_year
templates.env.globals["shrink_base_url"] = get_shrink_base_url


def load_user_pastes(request: Request) -> list[str]:
    user_pastes_cookie = request.cookies.get("user_pastes")
    if not user_pastes_cookie:
        return []

    if "." in user_pastes_cookie:
        payload = verify_signed_cookie_value(user_pastes_cookie)
        if payload is None:
            return []
        return parse_user_paste_ids(payload)

    return parse_user_paste_ids(user_pastes_cookie)


def parse_user_paste_ids(payload: str) -> list[str]:
    try:
        loaded_ids = json.loads(payload)
    except json.JSONDecodeError:
        return []

    if not isinstance(loaded_ids, list):
        return []

    return [
        paste_id for paste_id in loaded_ids if isinstance(paste_id, str) and paste_id
    ]


def order_recent_pastes(paste_ids: list[str]) -> list[str]:
    ordered_ids: list[str] = []
    seen: set[str] = set()

    for paste_id in reversed(paste_ids):
        if paste_id in seen:
            continue
        ordered_ids.append(paste_id)
        seen.add(paste_id)

    return ordered_ids


def encode_cookie_payload(payload: str) -> str:
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def decode_cookie_payload(payload: str) -> str | None:
    padding = "=" * (-len(payload) % 4)
    try:
        raw_payload = base64.urlsafe_b64decode(f"{payload}{padding}")
        return raw_payload.decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None


def sign_cookie_value(value: str) -> str:
    return hmac.new(
        settings.COOKIE_SIGNING_SECRET.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def dump_user_pastes_cookie(paste_ids: list[str]) -> str:
    normalized_ids = normalize_recent_pastes(paste_ids)
    payload = json.dumps(normalized_ids, separators=(",", ":"))
    encoded_payload = encode_cookie_payload(payload)
    signature = sign_cookie_value(encoded_payload)
    return f"{encoded_payload}.{signature}"


def verify_signed_cookie_value(cookie_value: str) -> str | None:
    encoded_payload, separator, signature = cookie_value.partition(".")
    if not separator or not signature:
        return None

    expected_signature = sign_cookie_value(encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    return decode_cookie_payload(encoded_payload)


def normalize_recent_pastes(paste_ids: list[str]) -> list[str]:
    recent_ids = order_recent_pastes(paste_ids)
    capped_recent_ids = recent_ids[: settings.MAX_RECENT_PASTES]
    return list(reversed(capped_recent_ids))


def normalize_newlines(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def build_paste_lines(content: str) -> list[dict[str, Any]]:
    normalized_content = normalize_newlines(content)
    return [
        {"number": line_number, "anchor": f"L{line_number}", "text": line_text}
        for line_number, line_text in enumerate(normalized_content.split("\n"), start=1)
    ]


def short_slug_from_url(short_url: str | None) -> str | None:
    """Extract the last path segment from a short URL (custom slug)."""
    if not short_url or not isinstance(short_url, str):
        return None
    slug = short_url.rstrip("/").rsplit("/", 1)[-1].strip()
    return slug or None


def paste_display_name(paste_id: str, short_url: str | None = None) -> str:
    """Human-facing paste name: custom short slug when set, otherwise paste id."""
    return short_slug_from_url(short_url) or str(paste_id)


def build_paste_summary(paste: dict[str, Any]) -> dict[str, Any]:
    normalized_content = normalize_newlines(str(paste.get("content", "")))
    preview_source = normalized_content.split("\n", 1)[0].strip()
    preview = preview_source if preview_source else "(empty first line)"
    if len(preview) > 120:
        preview = f"{preview[:117].rstrip()}..."
    created_at = paste.get("created_at")
    paste_id = str(paste["id"])
    short_url = paste.get("short_url")
    slug = short_slug_from_url(short_url if isinstance(short_url, str) else None)

    return {
        "id": paste_id,
        "short_url": short_url,
        "slug": slug,
        "display_name": paste_display_name(
            paste_id, short_url if isinstance(short_url, str) else None
        ),
        "created_at": created_at,
        "created_at_display": format_created_at(created_at),
        "preview": preview,
        "line_count": len(normalized_content.split("\n")) if normalized_content else 0,
    }


def format_created_at(created_at: Any) -> str:
    if isinstance(created_at, datetime):
        return created_at.strftime("%Y-%m-%d %H:%M")
    if created_at is None:
        return ""
    return str(created_at)


def resolve_public_base_url(request: Request) -> str:
    if settings.PUBLIC_BASE_URL:
        return settings.PUBLIC_BASE_URL.rstrip("/")
    return str(request.base_url).rstrip("/")


def build_absolute_app_url(request: Request, path: str, query: str = "") -> str:
    normalized_path = path if path.startswith("/") else f"/{path}"
    query_suffix = f"?{query}" if query else ""
    return f"{resolve_public_base_url(request)}{normalized_path}{query_suffix}"


def build_page_meta(
    request: Request,
    *,
    title: str,
    description: str = DEFAULT_META_DESCRIPTION,
    page_type: str = "website",
) -> dict[str, str]:
    preview_image_path = request.url_for("static", path=BRAND_PREVIEW_IMAGE_PATH).path
    return {
        "title": title,
        "description": description,
        "url": build_absolute_app_url(
            request, request.url.path, request.url.query or ""
        ),
        "image_url": build_absolute_app_url(request, preview_image_path),
        "image_alt": f"{APP_NAME} brand preview",
        "site_name": APP_NAME,
        "type": page_type,
    }


CUSTOM_SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def normalize_custom_slug(custom_slug: str | None) -> str | None:
    normalized_slug = (custom_slug or "").strip()
    if not normalized_slug:
        return None
    if not CUSTOM_SLUG_PATTERN.fullmatch(normalized_slug):
        raise HTTPException(status_code=400, detail="Invalid custom short link name")
    return normalized_slug


async def shorten_url(long_url: str, custom_slug: str | None = None) -> str | None:
    """Create a short URL via Shlink. Returns None when shrink is disabled or fails.

    Raises SlugTakenError when custom_slug is already in use (HTTP 400/409 from Shlink).
    """
    if not settings.SHRINK_URL or not settings.SHRINK_TOKEN:
        return None
    try:
        payload: dict[str, str] = {"longUrl": long_url}
        if custom_slug:
            payload["customSlug"] = custom_slug
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SHRINK_URL.rstrip('/')}/rest/v3/short-urls",
                json=payload,
                headers={"X-Api-Key": settings.SHRINK_TOKEN},
                timeout=5.0,
            )
            status_code = getattr(response, "status_code", None)
            if status_code in {400, 409} and custom_slug:
                body_text = (getattr(response, "text", None) or "").lower()
                # Shlink typically returns 400 with type containing "non-unique-slug"
                if (
                    status_code == 409
                    or "slug" in body_text
                    or "unique" in body_text
                    or "already" in body_text
                ):
                    raise SlugTakenError(custom_slug)
            response.raise_for_status()
            short_url = response.json().get("shortUrl", "")
            if not isinstance(short_url, str) or not short_url.startswith(
                ("https://", "http://")
            ):
                logger.warning(
                    "Shlink returned unexpected shortUrl value: %r", short_url
                )
                return None
            return short_url
    except SlugTakenError:
        raise
    except (httpx.HTTPError, KeyError, ValueError):
        logger.warning("Failed to shorten URL: %s", long_url, exc_info=True)
        return None


def generate_paste_id(database: Database) -> str:
    for _ in range(MAX_PASTE_ID_GENERATION_ATTEMPTS):
        paste_id = "".join(
            secrets.choice(SHORT_PASTE_ID_ALPHABET)
            for _ in range(SHORT_PASTE_ID_LENGTH)
        )
        if database.get_paste(paste_id) is None:
            return paste_id

    raise HTTPException(status_code=503, detail="Could not allocate paste id")


def load_changelog_markdown() -> str:
    """Load CHANGELOG.md from the container root or project root."""
    candidates = (
        BASE_DIR / "CHANGELOG.md",
        PROJECT_ROOT / "CHANGELOG.md",
        Path("/app/CHANGELOG.md"),
    )
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return "# Changelog\n\nChangelog file is not available in this build.\n"


@app.get(
    "/robots.txt",
    summary="Robots exclusion protocol",
    description="Инструкция для поисковых ботов о запрете индексации.",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def robots_txt():
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@app.get(
    "/",
    summary="Главная страница",
    description="Отображает форму для создания нового nopaste.",
)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        template_context(
            request,
            meta=build_page_meta(
                request,
                title="Nopaste — create and share text instantly",
            ),
        ),
    )


@app.get(
    "/api/changelog",
    summary="Changelog markdown",
    description="Raw CHANGELOG.md for the in-app modal.",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def api_changelog():
    return PlainTextResponse(
        content=load_changelog_markdown(),
        media_type="text/markdown; charset=utf-8",
    )


@app.get(
    "/nopaste_changelog",
    summary="Changelog",
    description="Permanent link — opens the app with the changelog modal.",
    response_class=None,
)
async def nopaste_changelog():
    # Keep the path stable; UI shows changelog as a modal on every page.
    return RedirectResponse(url="/#changelog", status_code=303)


@app.post(
    "/paste",
    summary="Создать новый nopaste",
    response_description="Перенаправление на страницу нового nopaste",
)
async def create_paste(
    request: Request,
    content: str = Form(..., description="Содержимое nopaste"),
    custom_slug: str | None = Form(
        None, description="Имя короткой ссылки, если настроен Shlink"
    ),
):
    lang = request_lang(request)
    custom_slug = normalize_custom_slug(custom_slug)
    if not content.strip():
        raise HTTPException(
            status_code=400, detail=i18n_t("errors.empty_content", lang)
        )
    if len(content.encode("utf-8")) > settings.MAX_PASTE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=i18n_t(
                "errors.content_too_large",
                lang,
                limit=settings.MAX_PASTE_SIZE_BYTES,
            ),
        )

    paste_id = generate_paste_id(db)
    paste_url = str(request.url_for("get_paste", paste_id=paste_id))
    try:
        short_url = await shorten_url(paste_url, custom_slug)
    except SlugTakenError:
        # On create, fall back to auto slug (or no short url) rather than fail paste
        short_url = await shorten_url(paste_url, None)
    db.save_paste(paste_id, content, short_url)
    logger.info("Created paste: id=%s, length=%s", paste_id, len(content))

    user_pastes = load_user_pastes(request)
    user_pastes.append(paste_id)

    response = RedirectResponse(url=f"/paste/{paste_id}", status_code=303)
    response.set_cookie(
        key="user_pastes",
        value=dump_user_pastes_cookie(user_pastes),
        httponly=True,
        max_age=31536000,  # 1 year
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@app.get(
    "/paste/{paste_id}",
    summary="Просмотреть nopaste",
    description="Отображает содержимое указанного nopaste.",
)
async def get_paste(request: Request, paste_id: str):
    paste = db.get_paste(paste_id)
    if not paste:
        return RedirectResponse(url="/", status_code=303)
    content = paste["content"]
    created_at = format_created_at(paste["created_at"])
    short_url = paste.get("short_url")
    display_name = paste_display_name(
        paste_id, short_url if isinstance(short_url, str) else None
    )
    highlighted_paste = build_highlighted_paste(content)
    logger.info("Retrieved paste: id=%s", paste_id)
    return templates.TemplateResponse(
        request,
        "paste.html",
        template_context(
            request,
            paste_id=paste_id,
            display_name=display_name,
            content=content,
            created_at=created_at,
            lines=highlighted_paste.lines,
            highlighted_language=highlighted_paste.language,
            is_markdown=highlighted_paste.is_markdown,
            short_url=short_url,
            meta=build_page_meta(
                request,
                title=f"Nopaste — {display_name}",
                description=(
                    f"Open paste {display_name} in Nopaste — a clean way to share text, "
                    "logs, notes, and configs."
                ),
            ),
        ),
    )


@app.post(
    "/paste/{paste_id}/slug",
    summary="Обновить имя короткой ссылки nopaste",
    description="Создает или обновляет короткую ссылку Shlink для существующего nopaste с новым custom slug.",
)
async def update_paste_slug(
    request: Request,
    paste_id: str,
    custom_slug: str = Form(..., description="Новое имя короткой ссылки"),
):
    lang = request_lang(request)
    paste = db.get_paste(paste_id)
    if not paste:
        raise HTTPException(
            status_code=404, detail=i18n_t("errors.paste_not_found", lang)
        )

    if not settings.shrink_enabled:
        raise HTTPException(
            status_code=503, detail=i18n_t("errors.shrink_disabled", lang)
        )

    try:
        normalized_slug = normalize_custom_slug(custom_slug)
    except HTTPException as exc:
        if exc.status_code == 400:
            raise HTTPException(
                status_code=400, detail=i18n_t("errors.slug_invalid", lang)
            ) from exc
        raise
    if not normalized_slug:
        raise HTTPException(status_code=400, detail=i18n_t("errors.slug_empty", lang))

    paste_url = str(request.url_for("get_paste", paste_id=paste_id))
    try:
        short_url = await shorten_url(paste_url, normalized_slug)
    except SlugTakenError:
        raise HTTPException(
            status_code=409, detail=i18n_t("errors.slug_taken", lang)
        ) from None
    if not short_url:
        raise HTTPException(
            status_code=500,
            detail=i18n_t("errors.shrink_unavailable", lang),
        )

    db.update_paste_short_url(paste_id, short_url)
    logger.info("Updated short_url for paste %s: %s", paste_id, short_url)
    return JSONResponse(
        content={"status": "ok", "short_url": short_url, "slug": normalized_slug}
    )


@app.get(
    "/raw/{paste_id}",
    summary="Получить исходный текст nopaste",
    description="Возвращает содержимое nopaste без HTML-обёртки.",
    response_class=PlainTextResponse,
)
@app.get(
    "/paste/{paste_id}/raw",
    summary="Получить исходный текст nopaste",
    description="Альтернативный URL для получения содержимого nopaste без HTML-обёртки.",
    response_class=PlainTextResponse,
)
async def get_raw_paste(request: Request, paste_id: str):
    paste = db.get_paste(paste_id)
    if not paste:
        raise HTTPException(
            status_code=404,
            detail=i18n_t("errors.paste_not_found", request_lang(request)),
        )
    logger.info("Retrieved raw paste: id=%s", paste_id)
    return PlainTextResponse(content=paste["content"])


@app.get(
    "/list",
    summary="Список моих nopaste",
    description="Отображает список nopaste пользователя.",
)
async def list_pastes(request: Request):
    user_pastes = order_recent_pastes(load_user_pastes(request))
    paste_records = db.get_user_pastes(user_pastes)
    pastes = [build_paste_summary(paste) for paste in paste_records]
    return templates.TemplateResponse(
        request,
        "list.html",
        template_context(
            request,
            pastes=pastes,
            meta=build_page_meta(
                request,
                title="Nopaste — your recent pastes",
                description="Browse the pastes saved in your recent Nopaste history.",
            ),
        ),
    )


@app.get("/health/live", tags=["Health"], include_in_schema=False)
async def liveness():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "alive"})


@app.get("/health/ready", tags=["Health"], include_in_schema=False)
async def readiness():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})


def main():
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.APP_PORT)


if __name__ == "__main__":
    main()
