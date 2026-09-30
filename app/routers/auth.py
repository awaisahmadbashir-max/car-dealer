from fastapi import HTTPException, status
from fastapi.routing import APIRouter

from app.dependencies.auth import OAuth2PasswordRequestFormDependency
from app.dependencies.db import DBDependency
from app.schema.api import APIResponse
from app.schema.auth import LoginSchema, TokenSchema, UserRegisterSchema, UserSchema
from app.services.auth import authenticate_user, create_user, get_user

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register")
async def register(body: UserRegisterSchema, db: DBDependency) -> APIResponse:
    if await get_user(db, body.email) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists"
        )
    user = await create_user(db, body)
    return APIResponse(detail="Registered", data=UserSchema.model_validate(user))


@auth_router.post("/swagger-login")
async def swagger_login(
    body: OAuth2PasswordRequestFormDependency,
    db: DBDependency,
) -> TokenSchema:
    access_token = await authenticate_user(db, body.username, body.password)
    return TokenSchema(access_token=access_token, token_type="bearer")


@auth_router.post("/login")
async def login(
    body: LoginSchema,
    db: DBDependency,
) -> APIResponse:
    access_token = await authenticate_user(db, body.email, body.password)
    return APIResponse(
        detail="Logged in",
        data=TokenSchema(access_token=access_token, token_type="bearer"),
    )
