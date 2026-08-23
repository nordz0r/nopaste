import logging
import re
import secrets
from datetime import datetime
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from cookies import (
    dump_user_pastes_cookie,
    load_user_pastes as parse_recent_paste_cookie,
    order_recent_pastes,
)
from database import Database, create_database_from_settings
from highlighting import (
    build_highlighted_paste,
    extract_markdown_title,
    markdown_to_plain_text,
    normalize_newlines,
    render_markdown_for_instant_view,
)
from i18n import client_bundle, resolve_lang, t as i18n_t
from rate_limit import InMemoryRateLimiter
from shlink import SlugTakenError, shorten_url
from versioning import load_asset_version as _load_asset_version

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHORT_PASTE_ID_LENGTH = 8
SHORT_PASTE_ID_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
MAX_PASTE_ID_GENERATION_ATTEMPTS = 20
PASTE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
CUSTOM_SLUG_MIN_LENGTH = 5
CUSTOM_SLUG_MAX_LENGTH = 64
CUSTOM_SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{3,62}[a-zA-Z0-9]$")
RESERVED_SLUGS = frozenset(
    {
        "api",
        "docs",
        "redoc",
        "openapi.json",
        "health",
        "live",
        "ready",
        "static",
        "raw",
        "paste",
        "list",
        "robots.txt",
        "rest",
        "admin",
        "changelog",
        "iv",
    }
)
APP_NAME = "Nopaste"
DEFAULT_META_DESCRIPTION = "Share text, logs, notes, and configs with Nopaste."
GITHUB_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRAND_PREVIEW_IMAGE_PATH = "images/goldfinches_logo.png"
APP_VERSION_ENV_VAR = "APP_VERSION"
DEFAULT_COOKIE_SECRET = "local-development-cookie-secret"
INSTANT_VIEW_EDITOR_HOST = "instantview.telegram.org"

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent


def iter_version_candidate_paths() -> list[Path]:
    return [
        PROJECT_ROOT / "pyproject.toml",
        BASE_DIR / "pyproject.toml",
    ]


def load_asset_version() -> str:
    return _load_asset_version(iter_version_candidate_paths())


APP_VERSION = load_asset_version()

app = FastAPI(
    title=APP_NAME,
    description="Self-hosted pastebin for text, logs, notes, and configs.",
    version=APP_VERSION,
    debug=settings.DEBUG,
)


def request_lang(request: Request) -> str:
    return resolve_lang(accept_language=request.headers.get("accept-language"))


def is_paste_page_path(path: str) -> bool:
    return bool(re.fullmatch(r"/(?:iv|paste)/[^/]+", path))


def is_raw_paste_path(path: str) -> bool:
    return bool(re.fullmatch(r"/(?:raw/[^/]+|paste/[^/]+/raw)", path))


def is_paste_content_path(path: str) -> bool:
    return is_paste_page_path(path) or is_raw_paste_path(path)


def is_telegram_bot_request(request: Request) -> bool:
    user_agent = request.headers.get("user-agent", "")
    return bool(re.search(r"\btelegrambot\b", user_agent, re.IGNORECASE))


def is_instant_view_editor_request(request: Request) -> bool:
    referer = request.headers.get("referer", "")
    if not referer:
        return False
    try:
        parsed_referer = urlsplit(referer)
        hostname = parsed_referer.hostname
    except ValueError:
        return False
    return parsed_referer.scheme == "https" and hostname == INSTANT_VIEW_EDITOR_HOST


def is_telegram_preview_request(request: Request) -> bool:
    return is_telegram_bot_request(request) or is_instant_view_editor_request(request)


def template_context(request: Request, **extra: Any) -> dict[str, Any]:
    lang = request_lang(request)
    is_paste_page = is_paste_page_path(request.url.path)
    is_telegram_preview = is_paste_page and is_telegram_preview_request(request)
    ctx: dict[str, Any] = {
        "request": request,
        "base_template": get_design_base_template(),
        "design_name": get_active_design_name(),
        "lang": lang,
        "t": lambda key, **kwargs: i18n_t(key, lang, **kwargs),
        "i18n_js": client_bundle(lang),
        "shrink_enabled": settings.shrink_enabled,
        "feedback_url": build_feedback_issue_url(request, lang),
        "is_telegram_preview_request": is_telegram_preview,
    }
    ctx.update(extra)
    return ctx


class CacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized == "sw.js":
            response.headers["Cache-Control"] = "no-cache"
            response.headers["Service-Worker-Allowed"] = "/static/"
        else:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


db = create_database_from_settings(settings)
logger.info("Paste storage backend: %s", db.backend_name)
if settings.COOKIE_SIGNING_SECRET == DEFAULT_COOKIE_SECRET:
    logger.warning(
        "COOKIE_SIGNING_SECRET is the default development value; "
        "set a unique secret before exposing this instance."
    )

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

    norm = (ip or "").strip().lower()
    if norm in {"testclient", "testserver", "localhost"}:
        norm = "127.0.0.1"

    try:
        client_ip = ip_address(norm)
    except ValueError:
        return False

    for entry in allowlist:
        try:
            if client_ip in ip_network(entry.strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def _docs_ip_candidates(request: Request) -> list[str]:
    candidates: list[str] = []
    if request.client and request.client.host:
        candidates.append(request.client.host)
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        candidates.append(fwd.split(",")[0].strip())
    return candidates


@app.middleware("http")
async def restrict_api_docs(request: Request, call_next):
    """Restrict /docs, /redoc, /openapi.json when DOCS_ALLOWLIST is set."""
    if request.url.path in {"/docs", "/redoc", "/openapi.json"}:
        for candidate in _docs_ip_candidates(request):
            if _is_ip_in_allowlist(candidate, settings.DOCS_ALLOWLIST):
                break
        else:
            return PlainTextResponse("Forbidden", status_code=403)

    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    is_paste_page = is_paste_page_path(path)
    is_paste_content = is_paste_content_path(path)
    if is_paste_content:
        # Paste bodies are user content and may vary by crawler/user-agent.
        # Keep the origin and any CDN from serving one request's headers/body
        # to another client. This is also required when the hostname is behind
        # a cache-enabled reverse proxy such as Cloudflare.
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        response.headers["CDN-Cache-Control"] = "no-store"
    if is_paste_page and is_telegram_preview_request(request):
        # Telegram needs to read the page metadata and semantic article source
        # to build a link preview/Instant View. Do not send an empty header:
        # an empty X-Robots-Tag value is invalid, so remove it entirely.
        if "X-Robots-Tag" in response.headers:
            del response.headers["X-Robots-Tag"]
    else:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"

    if is_paste_page and is_instant_view_editor_request(request):
        # The editor embeds the source page from instantview.telegram.org.
        # Keep the frame exception limited to that exact HTTPS origin.
        if "X-Frame-Options" in response.headers:
            del response.headers["X-Frame-Options"]
    else:
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    return response


def current_year() -> int:
    return datetime.now().year


def get_active_design_name() -> str:
    design = (settings.UI_DESIGN or "default").strip() or "default"
    return design


def get_design_base_template() -> str:
    return f"designs/{get_active_design_name()}/base.html"


templates.env.globals["asset_version"] = APP_VERSION
templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["current_year"] = current_year


def load_user_pastes(request: Request) -> list[str]:
    return parse_recent_paste_cookie(request.cookies.get("user_pastes"))


def short_slug_from_url(short_url: str | None) -> str | None:
    if not short_url or not isinstance(short_url, str):
        return None
    slug = short_url.rstrip("/").rsplit("/", 1)[-1].strip()
    return slug or None


def paste_display_name(paste_id: str, short_url: str | None = None) -> str:
    return short_slug_from_url(short_url) or str(paste_id)


def format_created_at(created_at: Any) -> str:
    if isinstance(created_at, datetime):
        return created_at.strftime("%Y-%m-%d %H:%M")
    if created_at is None:
        return ""
    return str(created_at)


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


def github_repo_slug() -> str | None:
    slug = (settings.GITHUB_REPO or "").strip().strip("/")
    if not slug or not GITHUB_REPO_PATTERN.fullmatch(slug):
        return None
    return slug


def build_feedback_issue_url(request: Request, lang: str) -> str | None:
    """Prefilled GitHub new-issue URL for the footer Feedback button."""
    repo = github_repo_slug()
    if not repo:
        return None

    page_path = request.url.path or "/"
    if lang == "ru":
        title = "Обратная связь"
        intro = "Опишите, что можно улучшить или что сломалось."
        env_heading = "Окружение"
        page_label = "Страница"
        lang_label = "Язык"
    else:
        title = "Feedback"
        intro = "Tell us what to improve or what broke."
        env_heading = "Environment"
        page_label = "Page"
        lang_label = "Language"

    body = (
        f"## {title}\n\n"
        f"{intro}\n\n"
        f"<!-- -->\n\n"
        f"---\n"
        f"### {env_heading}\n"
        f"- Nopaste: `{APP_VERSION}`\n"
        f"- {page_label}: `{page_path}`\n"
        f"- {lang_label}: `{lang}`\n"
    )
    query = urlencode(
        {
            "title": title,
            "labels": "feedback",
            "body": body,
        }
    )
    return f"https://github.com/{repo}/issues/new?{query}"


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


rate_limiter = InMemoryRateLimiter()


def check_rate_limit(request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(
        client_ip, settings.RATE_LIMIT_PER_MINUTE, window_seconds=60.0
    ):
        lang = request_lang(request)
        raise HTTPException(
            status_code=429,
            detail=i18n_t("errors.rate_limit_exceeded", lang),
            headers={"Retry-After": "60"},
        )


def normalize_custom_slug(custom_slug: str | None) -> str | None:
    normalized_slug = (custom_slug or "").strip()
    if not normalized_slug:
        return None
    if (
        len(normalized_slug) < CUSTOM_SLUG_MIN_LENGTH
        or len(normalized_slug) > CUSTOM_SLUG_MAX_LENGTH
        or not CUSTOM_SLUG_PATTERN.fullmatch(normalized_slug)
        or normalized_slug.lower() in RESERVED_SLUGS
    ):
        raise HTTPException(status_code=400, detail="Invalid custom short link name")
    return normalized_slug


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
    description="Tell search crawlers not to index this instance.",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def robots_txt():
    return PlainTextResponse(
        "User-agent: TelegramBot\n"
        "Allow: /paste/\n"
        "Allow: /static/\n\n"
        "User-agent: Twitterbot\n"
        "Allow: /paste/\n"
        "Allow: /static/\n\n"
        "User-agent: facebookexternalhit\n"
        "Allow: /paste/\n"
        "Allow: /static/\n\n"
        "User-agent: *\n"
        "Allow: /paste/\n"
        "Allow: /raw/\n"
        "Allow: /static/\n"
        "Allow: /robots.txt\n"
        "Disallow: /list\n"
        "Disallow: /docs\n"
        "Disallow: /redoc\n"
        "Disallow: /openapi.json\n"
    )


@app.get(
    "/",
    summary="Create paste",
    description="Form for creating a new paste.",
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
    response_class=RedirectResponse,
)
async def nopaste_changelog():
    return RedirectResponse(url="/#changelog", status_code=303)


@app.post(
    "/paste",
    summary="Create paste",
    response_description="Redirect to the new paste",
)
async def create_paste(
    request: Request,
    content: str = Form(..., description="Paste body"),
    custom_slug: str | None = Form(
        None, description="Custom short-link name when Shlink is configured"
    ),
):
    lang = request_lang(request)
    check_rate_limit(request)
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
        max_age=31536000,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@app.api_route(
    "/paste/{paste_id}",
    methods=["GET", "HEAD"],
    summary="View paste",
    description="Render a paste with syntax highlighting and line anchors.",
    include_in_schema=False,
)
async def get_paste(request: Request, paste_id: str):
    if not PASTE_ID_PATTERN.fullmatch(paste_id):
        return RedirectResponse(url="/", status_code=303)
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
    content_preview = build_content_preview(
        markdown_to_plain_text(content) if highlighted_paste.is_markdown else content
    )
    markdown_title = (
        extract_markdown_title(content) if highlighted_paste.is_markdown else ""
    )
    instant_view_markdown = (
        render_markdown_for_instant_view(
            content,
            omit_first_heading=bool(markdown_title),
        )
        if highlighted_paste.is_markdown
        else ""
    )
    instant_view_title = markdown_title or f"Paste {display_name or paste_id}"
    logger.info("Retrieved paste: id=%s", paste_id)
    template_name = (
        "paste_preview.html" if is_telegram_preview_request(request) else "paste.html"
    )
    return templates.TemplateResponse(
        request,
        template_name,
        template_context(
            request,
            paste_id=paste_id,
            display_name=display_name,
            content=content,
            created_at=created_at,
            lines=highlighted_paste.lines,
            highlighted_language=highlighted_paste.language,
            is_markdown=highlighted_paste.is_markdown,
            instant_view_markdown=instant_view_markdown,
            instant_view_title=instant_view_title,
            short_url=short_url,
            content_preview=content_preview,
            meta=build_page_meta(
                request,
                title=f"Nopaste — {display_name}",
                description=content_preview
                or (
                    f"Open paste {display_name} in Nopaste — a clean way to share text, "
                    "logs, notes, and configs."
                ),
                page_type="article",
            ),
        ),
    )


@app.post(
    "/paste/{paste_id}/slug",
    summary="Update short-link name",
    description="Create or replace the Shlink custom slug for an existing paste.",
)
async def update_paste_slug(
    request: Request,
    paste_id: str,
    custom_slug: str = Form(..., description="New short-link name"),
):
    lang = request_lang(request)
    check_rate_limit(request)
    if not PASTE_ID_PATTERN.fullmatch(paste_id):
        raise HTTPException(
            status_code=404, detail=i18n_t("errors.paste_not_found", lang)
        )
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
    summary="Raw paste",
    description="Return the paste body as plain text.",
    response_class=PlainTextResponse,
)
@app.get(
    "/paste/{paste_id}/raw",
    summary="Raw paste",
    description="Alternate URL for the paste body as plain text.",
    response_class=PlainTextResponse,
)
async def get_raw_paste(request: Request, paste_id: str):
    lang = request_lang(request)
    if not PASTE_ID_PATTERN.fullmatch(paste_id):
        raise HTTPException(
            status_code=404,
            detail=i18n_t("errors.paste_not_found", lang),
        )
    paste = db.get_paste(paste_id)
    if not paste:
        raise HTTPException(
            status_code=404,
            detail=i18n_t("errors.paste_not_found", lang),
        )
    logger.info("Retrieved raw paste: id=%s", paste_id)
    return PlainTextResponse(
        content=paste["content"],
        headers={"X-Content-Type-Options": "nosniff"},
    )


@app.get(
    "/list",
    summary="Recent pastes",
    description="Pastes stored in this browser's signed history cookie.",
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


def build_content_preview(content: str, max_length: int = 200) -> str:
    """Extract a short plain-text preview from paste content for OG descriptions."""
    normalized = normalize_newlines(content).strip()
    if not normalized:
        return ""
    # Take first few lines, collapse whitespace
    preview = " ".join(normalized.split())
    if len(preview) > max_length:
        return f"{preview[:max_length].rstrip()}…"
    return preview


@app.api_route(
    "/iv/{paste_id}",
    methods=["GET", "HEAD"],
    summary="Legacy Instant View URL",
    description="Redirect the old /iv/{id} path to the canonical paste URL.",
    include_in_schema=False,
)
async def get_paste_iv(request: Request, paste_id: str):
    if not PASTE_ID_PATTERN.fullmatch(paste_id):
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/paste/{paste_id}", status_code=301)


@app.get("/health/live", tags=["Health"], include_in_schema=False)
async def liveness():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "alive"})


@app.get("/health/ready", tags=["Health"], include_in_schema=False)
async def readiness():
    try:
        db.ping()
    except Exception:
        logger.exception("Readiness check failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})


def main():
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.APP_PORT)


if __name__ == "__main__":
    main()
