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
    CLICKHOUSE_DATABASE: str = "default"  # default Clickhouse database

    # default pairs to collect
    BINANCE_PAIRS: List[str] = [
        "BTCUSDT:10",
        "ETHUSDT:1",
        "XRPUSDT:0.001",
        "BCHUSDT:1",
        "LTCUSDT:0.1",
        "SOLUSDT:0.1",
        "ETCUSDT:0.1",
        "ALGOUSDT:0.001",
        "CRVUSDT:0.001",
        "ZECUSDT:0.1",
    ]


settings = Settings()

BINANCE_PAIRS = {
    "BTCUSDT": 1,
    "ETHUSDT": 2,
    "XRPUSDT": 3,
    "BCHUSDT": 4,
    "LTCUSDT": 5,
    "SOLUSDT": 6,
    "ETCUSDT": 7,
    "ALGOUSDT": 8,
    "CRVUSDT": 9,
    "ZECUSDT": 10,
}


EXCHANGES = {
    "Binance": 1,
}
