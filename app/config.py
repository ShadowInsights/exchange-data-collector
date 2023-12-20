from typing import Literal

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
    POSTGRES_POOL_SIZE: int
    POSTGRES_MAX_OVERFLOW: int
    POSTGRES_POOL_TIMEOUT: int
    POSTGRES_POOL_RECYCLE: int

    IS_TRADING_SESSION_VERIFICATION_REQUIRED: bool

    VOLUME_WORKER_JOB_INTERVAL: float
    DB_WORKER_JOB_INTERVAL: float
    ORDERS_WORKER_JOB_INTERVAL: float
    MAESTRO_LIVENESS_UPDATER_JOB_INTERVAL: float
    MAESTRO_PAIRS_RETRIEVAL_INTERVAL: float
    ORDERS_ANOMALIES_SUMMARY_JOB_INTERVAL: float

    VOLUME_ANOMALY_RATIO: float
    VOLUME_COMPARATIVE_ARRAY_SIZE: int
    ORDER_ANOMALY_MINIMUM_LIQUIDITY: float

    ORDERS_ANOMALIES_SUMMARY_RATIO: float
    ORDERS_ANOMALIES_SUMMARY_COMPARATIVE_ARRAY_SIZE: int

    TOP_N_ORDERS: int
    ORDER_ANOMALY_MULTIPLIER: float
    ANOMALIES_DETECTION_TTL: int
    ANOMALIES_OBSERVING_TTL: int
    ANOMALIES_OBSERVING_RATIO: float
    ANOMALIES_SIGNIFICANTLY_INCREASED_RATIO: float
    MAXIMUM_ORDER_BOOK_ANOMALIES: int
    OBSERVING_SAVED_LIMIT_ANOMALIES_RATIO: float

    DISCORD_WEBHOOKS: str
    DISCORD_DEPTH_EMBED_COLOR: str
    DISCORD_ORDER_ANOMALY_BID_EMBED_COLOR: str
    DISCORD_ORDER_ANOMALY_ASK_EMBED_COLOR: str
    DISCORD_ORDER_BOOK_ANOMALY_CANCELED_EMBED_COLOR: str | int
    DISCORD_ORDER_BOOK_ANOMALY_REALIZED_EMBED_COLOR: str | int
    DISCORD_ORDER_ANOMALIES_SUMMARY_EMBED_COLOR: str | int

    TELEGRAM_BOT_TOKENS: str
    TELEGRAM_CHAT_IDS: str

    MAESTRO_MAX_LIVENESS_GAP_SECONDS: int

    LOGGING_LEVEL: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"


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
