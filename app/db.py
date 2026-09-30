from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.configs import settings

engine_kwargs: dict = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 10,
    "pool_timeout": 30,
}
engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
