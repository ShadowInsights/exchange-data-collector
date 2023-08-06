import asyncio
import logging
import uuid
from decimal import Decimal

from clickhouse_driver import Client

from app.common.config import settings
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
ch_client = Client(
    host=settings.CLICKHOUSE_HOST, port=settings.CLICKHOUSE_PORT
)
launch_id = uuid.uuid4()

if __name__ == "__main__":
    logging.info("Starting data collection")
    try:
        for pair in settings.BINANCE_PAIRS:
            symbol = pair.split(":")[0]
            delimiter = Decimal(pair.split(":")[1])
            collector = BinanceExchangeCollector(
                launch_id, symbol, delimiter, ch_client
            )
            asyncio.run(collector.run())
    except KeyboardInterrupt:
        # Perform cleanup here (e.g., close any open connections)
        logging.info("\nInterrupted. Closing application...")
