from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str


settings = Settings()


def pg_dsn(
    host: str,
    db: str,
    port: int,
    username: str,
    password: str,
    schema: str,
) -> str:
    return f"{schema}{username}:{password}@{host}:{port}/{db}"


DB_CONNECTION_STRING = pg_dsn(
    host=settings.POSTGRES_HOST,
    db=settings.POSTGRES_DB,
    port=settings.POSTGRES_PORT,
    username=settings.POSTGRES_USERNAME,
    password=settings.POSTGRES_PASSWORD,
    schema="postgresql://",
)

DB_CONNECTION_STRING_ASYNC = pg_dsn(
    host=settings.POSTGRES_HOST,
    db=settings.POSTGRES_DB,
    port=settings.POSTGRES_PORT,
    username=settings.POSTGRES_USERNAME,
    password=settings.POSTGRES_PASSWORD,
    schema="postgresql+asyncpg://",
)
