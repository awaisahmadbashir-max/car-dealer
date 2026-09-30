from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs import settings
from app.models.user import User
from app.schema.auth import UserRegisterSchema
from app.utils.crypto import encrypt_password, verify_password
from app.utils.jwt import create_token


async def get_user(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> str:
    user = await get_user(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )
    access_token = create_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return access_token


async def create_user(db: AsyncSession, user: UserRegisterSchema) -> User:
    new_user = User(
        email=user.email,
        password_hash=encrypt_password(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
