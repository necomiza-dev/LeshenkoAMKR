# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from sqlalchemy import select   # <- добавлено
from .. import schemas, database, auth
from ..models import User
from ..auth import create_access_token

router = APIRouter(prefix="/auth", tags=["🔐 Аутентификация"])

@router.post(
    "/register",
    response_model=schemas.Token,
    summary="Регистрация нового пользователя",
    description="""
    Создаёт новый аккаунт в системе и возвращает JWT-токен для последующей авторизации.
    
    **Требования к данным:**
    - `username`: от 3 до 50 символов, уникальный
    - `password`: от 6 до 72 символов
    
    **Важно:**
    - Имя пользователя не может содержать спецсимволы (только буквы, цифры, подчёркивания)
    - Пароль чувствителен к регистру
    
    **Ответ:** Объект с полями `access_token` и `token_type`.
    """
)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    existing = await db.execute(
        select(User).where(User.username == user.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    hashed_pw = auth.hash_password(user.password)
    db_user = User(username=user.username, hashed_password=hashed_pw)
    db.add(db_user)
    await db.commit()
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post(
    "/login",
    response_model=schemas.Token,
    summary="Вход в систему",
    description="""
    Аутентифицирует пользователя по логину и паролю и выдаёт JWT-токен.
    
    **Требования:**
    - Правильное сочетание `username` и `password`
    - Пользователь должен быть зарегистрирован ранее
    
    **Использование токена:**
    - Передавайте токен в заголовке: `Authorization: Bearer <токен>`
    
    **Срок действия токена:** 30 минут.
    """
)
async def login(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    authenticated_user = await auth.authenticate_user(db, user.username, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": authenticated_user.username})
    return {"access_token": access_token, "token_type": "bearer"}
