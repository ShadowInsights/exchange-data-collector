from prometheus_client import start_http_server
import asyncio
import logging
import uuid
from decimal import Decimal
import socket

from app.common.config import settings
from app.db.database import ClickHousePool
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector

launch_id = uuid.uuid4()
ch_connection_pool = ClickHousePool(
    max_connections=settings.CLICKHOUSE_CONNECTION_POOL_SIZE
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(filename)s] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)


async def main():
    logging.info("Starting Prometheus server")
    start_http_server(8080)

    logging.info("Starting data collection")
    logging.info(f"Launch ID: {launch_id}")

    tasks = []  # List to store tasks
    for pair in settings.BINANCE_PAIRS:
        symbol = pair.split(":")[0]
        delimiter = Decimal(pair.split(":")[1])
        collector = BinanceExchangeCollector(
            launch_id, symbol, delimiter, ch_connection_pool
        )

        # Schedule the collector's task to run
        task = collector.run()
        tasks.append(task)

    # Use asyncio.gather to wait for all tasks to complete
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nInterrupted. Closing application...")
    except Exception as e:
        logging.exception(e)
        logging.info("Closing application...")
