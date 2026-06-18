import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import secrets
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from database import Database

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


# Кастомный класс для добавления заголовков кэширования
class CacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000"
        return response


db = Database(settings.DATABASE_PATH)

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static", CacheStaticFiles(directory=str(BASE_DIR / "static")), name="static"
)


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


APP_VERSION = load_asset_version()
templates.env.globals["asset_version"] = APP_VERSION
templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["current_year"] = current_year


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


def build_paste_summary(paste: dict[str, Any]) -> dict[str, Any]:
    normalized_content = normalize_newlines(str(paste.get("content", "")))
    preview_source = normalized_content.split("\n", 1)[0].strip()
    preview = preview_source if preview_source else "(empty first line)"
    if len(preview) > 120:
        preview = f"{preview[:117].rstrip()}..."
    created_at = paste.get("created_at")

    return {
        "id": str(paste["id"]),
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


async def shorten_url(long_url: str) -> str | None:
    if not settings.SHRINK_URL or not settings.SHRINK_TOKEN:
        return None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SHRINK_URL.rstrip('/')}/rest/v3/short-urls",
                json={"longUrl": long_url},
                headers={"X-Api-Key": settings.SHRINK_TOKEN},
                timeout=5.0,
            )
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
    except (httpx.HTTPError, KeyError):
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


@app.get(
    "/",
    summary="Главная страница",
    description="Отображает форму для создания нового nopaste.",
)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "base_template": get_design_base_template(),
            "design_name": get_active_design_name(),
            "meta": build_page_meta(
                request,
                title="Nopaste — create and share text instantly",
            ),
        },
    )


@app.post(
    "/paste",
    summary="Создать новый nopaste",
    response_description="Перенаправление на страницу нового nopaste",
)
async def create_paste(
    request: Request, content: str = Form(..., description="Содержимое nopaste")
):
    if not content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    if len(content.encode("utf-8")) > settings.MAX_PASTE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(f"Content exceeds the {settings.MAX_PASTE_SIZE_BYTES} byte limit"),
        )

    paste_id = generate_paste_id(db)
    paste_url = str(request.url_for("get_paste", paste_id=paste_id))
    short_url = await shorten_url(paste_url)
    db.save_paste(paste_id, content, short_url)
    logger.info("Created paste: id=%s, length=%s", paste_id, len(content))

    # Получаем текущие пасты пользователя из куки
    user_pastes = load_user_pastes(request)
    user_pastes.append(paste_id)

    # Создаем ответ с редиректом и устанавливаем куки
    response = RedirectResponse(url=f"/paste/{paste_id}", status_code=303)
    response.set_cookie(
        key="user_pastes",
        value=dump_user_pastes_cookie(user_pastes),
        httponly=True,
        max_age=31536000,  # 1 год
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
    logger.info("Retrieved paste: id=%s", paste_id)
    return templates.TemplateResponse(
        request,
        "paste.html",
        {
            "request": request,
            "base_template": get_design_base_template(),
            "design_name": get_active_design_name(),
            "paste_id": paste_id,
            "content": content,
            "created_at": created_at,
            "lines": build_paste_lines(content),
            "short_url": short_url,
            "meta": build_page_meta(
                request,
                title=f"Nopaste — paste {paste_id}",
                description=(
                    f"Open paste {paste_id} in Nopaste — a clean way to share text, "
                    "logs, notes, and configs."
                ),
            ),
        },
    )


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
        {
            "request": request,
            "base_template": get_design_base_template(),
            "design_name": get_active_design_name(),
            "pastes": pastes,
            "meta": build_page_meta(
                request,
                title="Nopaste — your recent pastes",
                description="Browse the pastes saved in your recent Nopaste history.",
            ),
        },
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
