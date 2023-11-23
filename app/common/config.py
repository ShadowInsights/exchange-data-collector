import logging

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()
# Configure logging
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
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 1800

    IS_TRADING_SESSION_VERIFICATION_REQUIRED: bool = False

    VOLUME_WORKER_JOB_INTERVAL: int = 5
    DB_WORKER_JOB_INTERVAL: int
    ORDERS_WORKER_JOB_INTERVAL: int = 1
    MAESTRO_LIVENESS_UPDATER_JOB_INTERVAL: int = 1
    MAESTRO_PAIRS_RETRIEVAL_INTERVAL: int = 1

    VOLUME_ANOMALY_RATIO: float
    VOLUME_COMPARATIVE_ARRAY_SIZE: int
    ORDER_ANOMALY_MINIMUM_LIQUIDITY: float

    TOP_N_ORDERS: int = 15
    ORDER_ANOMALY_MULTIPLIER: float = 10
    ANOMALIES_DETECTION_TTL: int = 900
    ANOMALIES_OBSERVING_TTL: int = 3600
    ANOMALIES_OBSERVING_RATIO: float = 0.2
    ANOMALIES_SIGNIFICANTLY_INCREASED_RATIO: float = 2
    MAXIMUM_ORDER_BOOK_ANOMALIES: int = 4
    OBSERVING_SAVED_LIMIT_ANOMALIES_RATIO: float = 0.2

    DISCORD_WEBHOOKS: str
    DISCORD_DEPTH_EMBED_COLOR: str
    DISCORD_ORDER_ANOMALY_BID_EMBED_COLOR: str
    DISCORD_ORDER_ANOMALY_ASK_EMBED_COLOR: str
    DISCORD_ORDER_BOOK_ANOMALY_CANCELED_EMBED_COLOR: str | int
    DISCORD_ORDER_BOOK_ANOMALY_REALIZED_EMBED_COLOR: str | int

    MAESTRO_MAX_LIVENESS_GAP_MINUTES: int = 1


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
