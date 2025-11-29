# app/web/routes.py
from fastapi import APIRouter, Request, Form, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from .. import database, auth, crud, schemas
from sqlalchemy import select
from pathlib import Path

# Путь к корню проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()

@router.get(
    "/",
    response_class=HTMLResponse,
    summary="Главная страница веб-интерфейса",
    description="""
    Перенаправляет пользователя:
    - Если авторизован → на список книг (`/web/books`)
    - Если не авторизован → на страницу входа (`/web/login`)
    
    Это корневой маршрут веб-интерфейса.
    """
)
async def web_home(request: Request):
    return RedirectResponse("/web/login", status_code=303)

@router.get(
    "/login",
    response_class=HTMLResponse,
    summary="Страница входа",
    description="""
    Отображает форму входа в систему.
    
    Пользователь может ввести имя пользователя и пароль.
    После успешного входа перенаправляется на `/web/books`.
    """
)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post(
    "/login",
    summary="Вход через веб-форму",
    description="""
    Обрабатывает отправку формы входа.
    
    Принимает:
    - `username`: имя пользователя
    - `password`: пароль
    
    При успехе:
    - Устанавливает куку с JWT-токеном
    - Перенаправляет на `/web/books`
    
    При ошибке:
    - Показывает сообщение об ошибке на той же странице
    """
)
async def login_web(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(database.get_db)
):
    user = await auth.authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверное имя пользователя или пароль"},
            status_code=401
        )
    token = auth.create_access_token(data={"sub": user.username})
    
    # УСТАНАВЛИВАЕМ КУКУ В САМ RedirectResponse!
    redirect_response = RedirectResponse("/web/books", status_code=303)
    auth.set_auth_cookie(redirect_response, token)
    return redirect_response

@router.get(
    "/register",
    response_class=HTMLResponse,
    summary="Страница регистрации",
    description="""
    Отображает форму регистрации нового аккаунта.
    
    Пользователь может создать учётную запись, указав:
    - Имя пользователя (3–50 символов)
    - Пароль (6–72 символа)
    
    После успешной регистрации перенаправляется на `/web/books`.
    """
)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post(
    "/register",
    summary="Регистрация через веб-форму",
    description="""
    Обрабатывает отправку формы регистрации.
    
    Принимает:
    - `username`: новое имя пользователя
    - `password`: новый пароль
    
    Валидация:
    - Длина имени: 3–50 символов
    - Длина пароля: 6–72 символа
    - Имя пользователя должно быть уникальным
    
    При успехе:
    - Создаёт пользователя в БД
    - Устанавливает куку с JWT-токеном
    - Перенаправляет на `/web/books`
    
    При ошибке:
    - Показывает сообщение на той же странице
    """
)
async def register_web(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(database.get_db)
):
    # Валидация
    if len(password.encode('utf-8')) > 72:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пароль слишком длинный (максимум 72 байта)"},
            status_code=400
        )
    if len(username) < 3 or len(username) > 50:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Имя пользователя должно быть от 3 до 50 символов"},
            status_code=400
        )

    # Проверка существования
    existing = await db.execute(select(auth.models.User).where(auth.models.User.username == username))
    if existing.scalar_one_or_none():
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Имя пользователя уже занято"},
            status_code=400
        )

    # Создание пользователя
    hashed_pw = auth.hash_password(password)
    db_user = auth.models.User(username=username, hashed_password=hashed_pw)
    db.add(db_user)
    await db.commit()
    
    # Установка куки и редирект
    token = auth.create_access_token(data={"sub": username})
    
    # УСТАНАВЛИВАЕМ КУКУ В САМ RedirectResponse!
    redirect_response = RedirectResponse("/web/books", status_code=303)
    auth.set_auth_cookie(redirect_response, token)
    return redirect_response

@router.get(
    "/books",
    response_class=HTMLResponse,
    summary="Список книг (веб-интерфейс)",
    description="""
    Отображает список всех книг текущего пользователя.
    
    Функционал:
    - Поиск по названию или автору (через параметр `q`)
    - Кнопки «Изменить» и «Удалить» для каждой книги
    - Кнопка «Добавить книгу»
    
    Доступ: Только для авторизованных пользователей.
    """
)
async def books_list(
    request: Request,
    q: str = None,
    db: AsyncSession = Depends(database.get_db)
):
    user = await auth.get_current_user_web(request, db)
    if not user:
        return RedirectResponse("/web/login", status_code=303)
    
    books = await crud.get_books(db, user.id, search=q)
    return templates.TemplateResponse("books.html", {
        "request": request,
        "books": books,
        "search_query": q
    })

@router.get(
    "/books/new",
    response_class=HTMLResponse,
    summary="Форма добавления новой книги",
    description="""
    Отображает форму для добавления новой книги.
    
    Поля:
    - Название книги (до 200 символов)
    - Автор (до 100 символов)
    
    После отправки форма создаёт книгу и перенаправляет на `/web/books`.
    
    Доступ: Только для авторизованных пользователей.
    """
)
async def add_book_form(request: Request, db: AsyncSession = Depends(database.get_db)):
    user = await auth.get_current_user_web(request, db)
    if not user:
        return RedirectResponse("/web/login", status_code=303)
    return templates.TemplateResponse("add_book.html", {"request": request})

@router.post(
    "/books/create",
    summary="Создание книги через веб-форму",
    description="""
    Обрабатывает отправку формы создания новой книги.
    
    Принимает:
    - `title`: название книги
    - `author`: имя автора
    
    После успешного создания перенаправляет на `/web/books`.
    
    Доступ: Только для авторизованных пользователей.
    """
)
async def create_book_web(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    db: AsyncSession = Depends(database.get_db)
):
    user = await auth.get_current_user_web(request, db)
    if not user:
        return RedirectResponse("/web/login", status_code=303)
    book_in = schemas.BookCreate(title=title, author=author)
    await crud.create_book(db, book_in, user.id)
    return RedirectResponse("/web/books", status_code=303)

@router.get(
    "/books/{book_id}/edit",
    response_class=HTMLResponse,
    summary="Форма редактирования книги",
    description="""
    Отображает форму для редактирования существующей книги.
    
    Поля предзаполнены данными книги.
    После отправки форма обновляет книгу и перенаправляет на `/web/books`.
    
    Доступ: Только владелец книги (авторизованный пользователь).
    """
)
async def edit_book_form(
    request: Request,
    book_id: int,
    db: AsyncSession = Depends(database.get_db)
):
    user = await auth.get_current_user_web(request, db)
    if not user:
        return RedirectResponse("/web/login", status_code=303)
    book = await crud.get_book_by_id(db, book_id, user.id)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return templates.TemplateResponse("edit_book.html", {"request": request, "book": book})

@router.post(
    "/books/{book_id}/update",
    summary="Обновление книги через веб-форму",
    description="""
    Обрабатывает отправку формы обновления книги.
    
    Принимает:
    - `title` (опционально): новое название
    - `author` (опционально): новый автор
    
    После успешного обновления перенаправляет на `/web/books`.
    
    Доступ: Только владелец книги (авторизованный пользователь).
    """
)
async def update_book_web(
    book_id: int,
    title: str = Form(...),
    author: str = Form(...),
    request: Request = None,
    db: AsyncSession = Depends(database.get_db)
):
    user = await auth.get_current_user_web(request, db)
    if not user:
        return RedirectResponse("/web/login", status_code=303)
    book_update = schemas.BookUpdate(title=title, author=author)
    updated = await crud.update_book(db, book_id, book_update, user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return RedirectResponse("/web/books", status_code=303)

@router.post(
    "/books/{book_id}/delete",
    summary="Удаление книги через веб-форму",
    description="""
    Обрабатывает удаление книги по её идентификатору.
    
    После успешного удаления перенаправляет на `/web/books`.
    
    Доступ: Только владелец книги (авторизованный пользователь).
    """
)
async def delete_book_web(
    book_id: int,
    request: Request,
    db: AsyncSession = Depends(database.get_db)
):
    user = await auth.get_current_user_web(request, db)
    if not user:
        return RedirectResponse("/web/login", status_code=303)
    success = await crud.delete_book(db, book_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return RedirectResponse("/web/books", status_code=303)

@router.get(
    "/logout",
    summary="Выход из системы",
    description="""
    Удаляет куку с JWT-токеном и перенаправляет на главную страницу.
    
    После выхода пользователь должен снова войти, чтобы получить доступ к своим книгам.
    """
)
async def logout(response: Response):
    response = RedirectResponse("/web/login", status_code=303)
    response.delete_cookie("library_token")
    return response