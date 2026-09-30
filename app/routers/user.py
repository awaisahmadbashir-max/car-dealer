from fastapi.routing import APIRouter

from app.dependencies.auth import AuthUserDependency
from app.schema.api import APIResponse
from app.schema.auth import UserSchema

user_router = APIRouter(prefix="/user", tags=["user"])


@user_router.get("/me")
async def me(user: AuthUserDependency) -> APIResponse:
    return APIResponse(detail="OK", data=UserSchema.model_validate(user))
