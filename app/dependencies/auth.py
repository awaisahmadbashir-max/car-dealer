from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.dependencies.db import DBDependency
from app.models.user import User
from app.services.auth import get_user
from app.utils.jwt import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/swagger-login")
OAuth2TokenDependency = Annotated[str, Depends(oauth2_scheme)]
OAuth2PasswordRequestFormDependency = Annotated[OAuth2PasswordRequestForm, Depends()]


async def get_current_user(
    token: OAuth2TokenDependency,
    db: DBDependency,
) -> User:
    email = decode_token(token)

    user = await get_user(db, email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    return user


AuthUserDependency = Annotated[User, Depends(get_current_user)]
AuthDependency = Depends(get_current_user)
