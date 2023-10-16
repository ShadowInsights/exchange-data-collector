import asyncio
import logging
import uuid

from prometheus_client import start_http_server

from app.common.database import get_async_db
from app.db.repositories.pair_repository import find_all_pairs
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector
from app.services.starters.liquidity_starters import \
    fill_missed_liquidity_intervals

launch_id = uuid.uuid4()


def start_metrics_server() -> None:
    logging.info("Starting metrics server")

    start_http_server(8080)

    logging.info("Metrics server started")


async def main() -> None:
    await fill_missed_liquidity_intervals()
    await start_collectors()


async def start_collectors() -> None:
    logging.info("Starting data collection")
    logging.info(f"Launch ID: {launch_id}")

    tasks = []  # List to store tasks
    pairs = []  # List to store pairs

    async with get_async_db() as session:
        pairs = await find_all_pairs(session)

    for pair in pairs:
        collector = BinanceExchangeCollector(
            launch_id=launch_id,
            pair_id=pair.id,
            exchange_id=pair.exchange_id,
            symbol=pair.symbol,
            delimiter=pair.delimiter,
        )

        # Schedule the collector's task to run
        task = collector.run()
        tasks.append(task)

    # Use asyncio.gather to wait for all tasks to complete
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.info("Starting application...")

    try:
        start_metrics_server()
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nInterrupted. Closing application...")
    except Exception as e:
        logging.exception(e)
        logging.info("Closing application...")
