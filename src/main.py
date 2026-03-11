import base64
import binascii
import hashlib
import hmac
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nopaste API",
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
db.init_db()

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static", CacheStaticFiles(directory=str(BASE_DIR / "static")), name="static"
)


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


@app.get(
    "/",
    summary="Главная страница",
    description="Отображает форму для создания нового nopaste.",
)
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


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

    paste_id = uuid4().hex
    db.save_paste(paste_id, content)
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
    logger.info("Retrieved paste: id=%s", paste_id)
    return templates.TemplateResponse(
        request,
        "paste.html",
        {
            "request": request,
            "paste_id": paste_id,
            "content": content,
            "created_at": created_at,
            "lines": build_paste_lines(content),
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
        request, "list.html", {"request": request, "pastes": pastes}
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
