# app/api/books.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .. import crud, schemas, database
from ..auth import get_current_user

router = APIRouter(prefix="/books", tags=["📚 Книги"])

@router.post(
    "/",
    response_model=schemas.BookResponse,
    summary="Добавить новую книгу",
    description="""
    Создаёт новую запись о книге в вашей персональной библиотеке.
    
    **Требования:**
    - Название книги (1–200 символов)
    - Имя автора (1–100 символов)
    
    **Доступ:** Только для авторизованных пользователей.
    """
)
async def create_book(
    book: schemas.BookCreate,
    db: AsyncSession = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    return await crud.create_book(db, book, current_user.id)

@router.get(
    "/",
    response_model=List[schemas.BookResponse],
    summary="Получить все книги",
    description="""
    Возвращает список всех книг, принадлежащих текущему пользователю.
    
    **Опционально:**
    - Параметр `search` позволяет искать книги по названию или автору (регистронезависимо).
    
    **Пример поиска:**
    ```
    GET /api/books?search=Гарри
    ```
    
    **Доступ:** Только для авторизованных пользователей.
    """
)
async def read_books(
    search: str = Query(None, description="Поиск по названию или автору"),
    db: AsyncSession = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    return await crud.get_books(db, current_user.id, search=search)


@router.put(
    "/{book_id}",
    response_model=schemas.BookResponse,
    summary="Обновить информацию о книге",
    description="""
    Обновляет данные существующей книги: название и/или автора.
    
    **Параметры пути:**
    - `book_id`: уникальный идентификатор книги (целое число)
    
    **Тело запроса:**
    - `title` (опционально): новое название книги
    - `author` (опционально): новое имя автора
    
    **Доступ:** Только владелец книги (авторизованный пользователь).
    """
)
async def update_book(
    book_id: int,
    book_update: schemas.BookUpdate,
    db: AsyncSession = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    book = await crud.update_book(db, book_id, book_update, current_user.id)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена или не принадлежит вам")
    return book

@router.delete(
    "/{book_id}",
    summary="Удалить книгу",
    description="""
    Удаляет книгу из вашей библиотеки по её уникальному идентификатору.
    
    **Параметры пути:**
    - `book_id`: уникальный идентификатор книги (целое число)
    
    **Ответ:**
    - Успешное удаление возвращает JSON: `{"detail": "Книга удалена"}`
    
    **Доступ:** Только владелец книги (авторизованный пользователь).
    """
)
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    success = await crud.delete_book(db, book_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Книга не найдена или не принадлежит вам")
    return {"detail": "Книга удалена"}