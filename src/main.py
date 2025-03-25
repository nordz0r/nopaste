from fastapi import FastAPI, Request, HTTPException, Form, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from config import settings
from pathlib import Path

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

storage = {}
new_pastes = set()  # Временное хранилище для новых paste

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", CacheStaticFiles(directory=str(BASE_DIR / "static")), name="static")

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
async def create_paste(request: Request, content: str = Form(..., description="Содержимое nopaste")):
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    paste_id = str(uuid4())[:8]
    storage[paste_id] = content
    new_pastes.add(paste_id)  # Отмечаем paste как новый
    url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/paste/{paste_id}"
    return RedirectResponse(url=url, status_code=303)

@app.get(
    "/paste/{paste_id}",
    summary="Просмотреть nopaste",
    description="Отображает содержимое указанного nopaste.",
)
async def get_paste(request: Request, paste_id: str):
    content = storage.get(paste_id)
    if not content:
        return RedirectResponse(url="/", status_code=303)
    # Проверяем, новый ли paste, и сразу убираем из списка новых
    is_new = paste_id in new_pastes
    if is_new:
        new_pastes.remove(paste_id)
    return templates.TemplateResponse(
        request,
        "paste.html",
        {"request": request, "paste_id": paste_id, "content": content, "is_new": is_new},
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
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})

def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.APP_PORT)

if __name__ == "__main__":
    main()