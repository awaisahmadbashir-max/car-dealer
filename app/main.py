import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.configs import settings
from app.routers.api import api_router
from app.schema.api import APIResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.services.catalog import CatalogError, get_catalog

    try:
        catalog = get_catalog()
    except CatalogError as exc:
        logger.error("Car catalog unavailable: %s", exc)
    else:
        logger.info(
            "Loaded %s cars and %s dealers",
            len(catalog.cars),
            len(catalog.dealers),
        )
    yield


app = FastAPI(title="Car Dealer Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
async def health():
    return APIResponse(detail="OK")


if settings.STATIC_DIR.is_dir():
    app.mount(
        "/", StaticFiles(directory=str(settings.STATIC_DIR), html=True), name="static"
    )
