from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    CLICKHOUSE_HOST: str = "localhost"  # default Clickhouse host
    CLICKHOUSE_PORT: int = 9000  # default Clickhouse port

    # default pairs to collect
    BINANCE_PAIRS: List[str] = ["BTCUSDT", "ETHUSDT"]


settings = Settings()
