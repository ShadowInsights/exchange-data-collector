import asyncio
import logging
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from prometheus_client import start_http_server

from app.common.database import get_async_db
from app.db.repositories.pair_repository import find_all_pairs
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector
from app.workers.order_book_worker import order_book_table_truncate_and_backup

launch_id = uuid.uuid4()


def start_metrics_server():
    logging.info("Starting metrics server")

    start_http_server(8000)

    logging.info("Metrics server started")


def start_scheduler():
    logging.info("Starting scheduler")

    scheduler = BackgroundScheduler()
    trigger = CronTrigger(hour=22, minute=30, second=0, timezone="UTC")
    scheduler.add_job(order_book_table_truncate_and_backup, trigger=trigger)
    scheduler.start()

    logging.info("Scheduler started")


async def start_collectors():
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
        start_scheduler()
        asyncio.run(start_collectors())
    except KeyboardInterrupt:
        logging.info("\nInterrupted. Closing application...")
    except Exception as e:
        logging.exception(e)
        logging.info("Closing application...")
