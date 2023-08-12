from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    CLICKHOUSE_HOST: str = "localhost"  # default Clickhouse host
    CLICKHOUSE_PORT: int = 9000  # default Clickhouse port
    CLICKHOUSE_USERNAME: str = "default"  # default Clickhouse user
    CLICKHOUSE_PASSWORD: str = ""  # default Clickhouse password
    CLICKHOUSE_CONNECTION_POOL_SIZE: int = 10  # default Clickhouse user

    # default pairs to collect
    BINANCE_PAIRS: List[str] = ["BTCUSDT:10"]


settings = Settings()

BINANCE_PAIRS = {
    "BTCUSDT": 1,
    "ETHUSDT": 2,
    "XRPUSDT": 3,
}


EXCHANGES = {
    "Binance": 1,
}
