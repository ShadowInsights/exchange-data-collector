import logging

from celery import Celery
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

    REDIS_HOST: str
    REDIS_PORT: str

    GOOGLE_APPLICATION_CREDENTIALS: str
    GOOGLE_CLOUD_BUCKET_NAME: str

    ORDER_BOOKS_TABLE_DUMP_LIMIT: int
    ORDER_BOOKS_TABLE_DUMP_BUFFER_MAX_SIZE: int


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

celery = Celery(
    "exchange-data-collector",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)

celery.conf.ONCE = {
    "backend": "celery_once.backends.Redis",
    "settings": {
        "url": f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
        "default_timeout": 60 * 60,  # 1 hour by default, change as needed
    },
}
