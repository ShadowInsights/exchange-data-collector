import logging

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(filename)s] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)


class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str

    PYTHON_ENV: str | None = None

    # GOOGLE_APPLICATION_CREDENTIALS: str
    GOOGLE_CLOUD_BUCKET_NAME: str

    ORDER_BOOKS_TABLE_DUMP_LIMIT: int
    ORDER_BOOKS_TABLE_DUMP_BUFFER_MAX_SIZE: int

    LIQUIDITY_WORKER_JOB_INTERVAL: int = 5
    DB_WORKER_JOB_INTERVAL: int

    LIQUIDITY_ANOMALY_RATIO: int
    COMPARABLE_LIQUIDITY_SET_SIZE: int

    DISCORD_WEBHOOKS: str
    DISCORD_EMBED_COLOR: str


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
