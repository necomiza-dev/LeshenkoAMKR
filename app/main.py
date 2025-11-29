# app/main.py
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .database import Base, engine
from .web import routes as web_routes
from .api import books, auth
from .auth import get_current_user_web
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db

app = FastAPI(
    title="Home Library API",
    description="A clean, secure, and async API for managing your personal book collection with JWT auth and web UI.",
    version="1.0.0"
)

@app.on_event("startup")
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Путь к статике (корень проекта)
BASE_DIR = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ПОДКЛЮЧАЕМ РОУТЕРЫ
app.include_router(web_routes.router, prefix="/web")  # Веб-интерфейс
app.include_router(books.router, prefix="/api")       # API для книг
app.include_router(auth.router, prefix="/api")        # API для аутентификации

@app.get("/", include_in_schema=False)
async def root_redirect(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user_web(request, db)
    if user:
        return RedirectResponse("/web/books", status_code=303)
    else:
        return RedirectResponse("/web/login", status_code=303)