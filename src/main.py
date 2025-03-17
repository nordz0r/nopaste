from fastapi import FastAPI, Request, HTTPException, Form, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from config import settings  # Импортируем настройки из config.py
from pathlib import Path  # Добавляем импорт pathlib

app = FastAPI(
    title="Nopaste API",
    description="API для простого nopaste приложения",
    version="1.0.0",
    debug=settings.DEBUG,  # Используем настройку DEBUG
)

storage = {}

# Получаем путь к директории с шаблонами
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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
async def create_paste(content: str = Form(..., description="Содержимое nopaste")):
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    paste_id = str(uuid4())[:8]
    storage[paste_id] = content
    return RedirectResponse(url=f"/paste/{paste_id}", status_code=303)


@app.get(
    "/paste/{paste_id}",
    summary="Просмотреть nopaste",
    description="Отображает содержимое указанного nopaste.",
)
async def get_paste(request: Request, paste_id: str):
    content = storage.get(paste_id)
    if not content:
        raise HTTPException(status_code=404, detail="Paste not found")
    return templates.TemplateResponse(
        request, "paste.html", {"request": request, "paste_id": paste_id, "content": content}
    )


@app.get(
    "/list",
    summary="Список всех nopaste",
    description="Отображает список всех созданных nopaste.",
)
async def list_pastes(request: Request):
    pastes = list(storage.keys())
    return templates.TemplateResponse(
        request, "list.html", {"request": request, "pastes": pastes}
    )


@app.get("/health/live", tags=["Health"], include_in_schema=False)
async def liveness():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "alive"})


@app.get("/health/ready", tags=["Health"], include_in_schema=False)
async def readiness():
    # Здесь вы можете добавить проверки доступности зависимостей
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})


def main():
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.APP_PORT)


if __name__ == "__main__":
    main()
