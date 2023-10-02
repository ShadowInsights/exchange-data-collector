import asyncio
import logging
import multiprocessing
import os
import uuid

from prometheus_client import start_http_server

from app.common.database import get_async_db
from app.db.repositories.pair_repository import find_all_pairs
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector

launch_id = uuid.uuid4()


def run_celery_worker():
    os.system("celery -A app.common.worker.worker worker --loglevel=info")


def run_celery_beat():
    os.system("celery -A app.common.worker.worker beat --loglevel=info")


async def main():
    logging.info("Starting Prometheus server")
    start_http_server(8080)

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

    logging.info("Starting Celery worker and beat")
    worker_process = multiprocessing.Process(target=run_celery_worker)
    worker_process.start()

    beat_process = multiprocessing.Process(target=run_celery_beat)
    beat_process.start()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nInterrupted. Closing application...")
    except Exception as e:
        logging.exception(e)
        logging.info("Closing application...")
