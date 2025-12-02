from fastapi import FastAPI, Request, HTTPException, Form, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from config import settings
from pathlib import Path
import json
from database import Database
import logging
logging.basicConfig(level=logging.INFO)
from datetime import datetime, timedelta

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
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    paste_id = str(uuid4())[:8]
    db.save_paste(paste_id, content)
    logging.info(f"Created paste: id={paste_id}, length={len(content)}")

    # Получаем текущие пасты пользователя из куки
    user_pastes_cookie = request.cookies.get("user_pastes")
    if user_pastes_cookie:
        try:
            user_pastes = json.loads(user_pastes_cookie)
        except json.JSONDecodeError:
            user_pastes = []
    else:
        user_pastes = []

    # Добавляем новый paste_id
    user_pastes.append(paste_id)

    # Формируем URL без явного указания порта, если он None
    base_url = f"{request.url.scheme}://{request.url.hostname}"
    if request.url.port and request.url.port not in (80, 443):
        base_url += f":{request.url.port}"
    url = f"{base_url}/paste/{paste_id}"

    # Создаем ответ с редиректом и устанавливаем куки
    response = RedirectResponse(url=url, status_code=303)
    response.set_cookie(
        key="user_pastes",
        value=json.dumps(user_pastes),
        httponly=True,
        max_age=31536000  # 1 год
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
    created_at = paste["created_at"]
    logging.info(f"Retrieved paste: id={paste_id}")
    return templates.TemplateResponse(
        request,
        "paste.html",
        {
            "request": request,
            "paste_id": paste_id,
            "content": content,
        },
    )


@app.get(
    "/list",
    summary="Список моих nopaste",
    description="Отображает список nopaste пользователя.",
)
async def list_pastes(request: Request):
    user_pastes_cookie = request.cookies.get("user_pastes")
    if user_pastes_cookie:
        try:
            user_pastes = json.loads(user_pastes_cookie)
        except json.JSONDecodeError:
            user_pastes = []
    else:
        user_pastes = []
    paste_records = db.get_user_pastes(user_pastes)
    pastes = [p["id"] for p in paste_records]
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
