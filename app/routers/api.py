from fastapi.routing import APIRouter

from app.routers.auth import auth_router
from app.routers.conversation import conversation_router
from app.routers.user import user_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(conversation_router)
