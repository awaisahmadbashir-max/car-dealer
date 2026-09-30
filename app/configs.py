from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


class Settings(BaseSettings):
    DATABASE_URL: str

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 5  # 5 hours
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 1  # 1 day

    MODEL_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    MODEL_API_KEY: str
    MODEL_CHAT_NAME: str = "gemini-2.5-flash"
    MODEL_EMBEDDING_NAME: str = "gemini-embedding-2"

    ROOT_DIR: Path = Path(__file__).resolve().parent.parent
    CARS_CSV: Path = ROOT_DIR / "inputs" / "cars.csv"
    DEALERS_CSV: Path = ROOT_DIR / "inputs" / "dealers.csv"

    STATIC_DIR_NAME: str = "static"
    STATIC_DIR: Path = ROOT_DIR / STATIC_DIR_NAME

    # Comma-separated origins for browser clients (e.g. Vite dev server).
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "https://f7q8c4lw-5173.inc1.devtunnels.ms"
    )
    # Any Microsoft dev tunnel host, so a new tunnel id does not need a code change.
    CORS_ORIGIN_REGEX: str = r"https://.*\.devtunnels\.ms"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def force_normalize(cls, v):
        if isinstance(v, str):
            return normalize_database_url(v)
        return v


settings = Settings()
