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

    IS_TRADING_SESSION_VERIFICATION_REQUIRED: bool = False

    LIQUIDITY_WORKER_JOB_INTERVAL: int = 5
    DB_WORKER_JOB_INTERVAL: int
    ORDERS_WORKER_JOB_INTERVAL: int = 1
    MAESTRO_LIVENESS_UPDATER_JOB_INTERVAL: int = 1
    MAESTRO_PAIRS_RETRIEVAL_INTERVAL: int = 1

    LIQUIDITY_ANOMALY_RATIO: float
    COMPARABLE_LIQUIDITY_SET_SIZE: int

    TOP_N_ORDERS: int = 15
    ORDER_ANOMALY_MULTIPLIER: float = 10
    ANOMALIES_DETECTION_TTL: int = 900
    ANOMALIES_OBSERVING_TTL: int = 3600
    ANOMALIES_OBSERVING_RATIO: float = 0.2

    DISCORD_WEBHOOKS: str
    DISCORD_DEPTH_EMBED_COLOR: str
    DISCORD_ORDER_ANOMALY_BID_EMBED_COLOR: str
    DISCORD_ORDER_ANOMALY_ASK_EMBED_COLOR: str


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
