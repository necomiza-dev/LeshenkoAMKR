from fastapi import FastAPI, Request, Depends, Response
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
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

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        if request.url.path.startswith("/api"):
            return JSONResponse(
                status_code=404,
                content={"detail": "API endpoint not found"}
            )
        else:
            templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404
            )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )