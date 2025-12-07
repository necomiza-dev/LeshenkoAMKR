# app/crud.py
from sqlalchemy.future import select
from sqlalchemy import or_
from . import models
from .schemas import BookCreate, BookUpdate
from sqlalchemy.ext.asyncio import AsyncSession

async def create_book(db: AsyncSession, book: BookCreate, owner_id: int):
    db_book = models.Book(
        title=book.title,
        author=book.author,
        description=book.description if book.description is not None else "",
        owner_id=owner_id
    )
    db.add(db_book)
    await db.commit()
    await db.refresh(db_book)
    return db_book

async def get_books(db: AsyncSession, owner_id: int, skip: int = 0, limit: int = 100, search: str = None):
    query = select(models.Book).where(models.Book.owner_id == owner_id)
    if search:
        query = query.where(
            or_(
                models.Book.title.ilike(f"%{search}%"),
                models.Book.author.ilike(f"%{search}%")
            )
        )
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def get_book_by_id(db: AsyncSession, book_id: int, owner_id: int):
    result = await db.execute(
        select(models.Book).where(models.Book.id == book_id, models.Book.owner_id == owner_id)
    )
    return result.scalar_one_or_none()

async def update_book(db: AsyncSession, book_id: int, book_update: BookUpdate, owner_id: int):
    book = await get_book_by_id(db, book_id, owner_id)
    if not book:
        return None
    for key, value in book_update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(book, key, value)
    await db.commit()
    await db.refresh(book)
    return book

async def delete_book(db: AsyncSession, book_id: int, owner_id: int) -> bool:
    book = await get_book_by_id(db, book_id, owner_id)
    if not book:
        return False
    await db.delete(book)
    await db.commit()
    return True