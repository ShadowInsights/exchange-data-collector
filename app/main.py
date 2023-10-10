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
from app.services.collectors.workers.liquidity_worker import \
    fill_missed_liquidity_intervals
from app.services.messengers.discord_messenger import DiscordMessenger
from app.workers.order_book_worker import order_book_table_truncate_and_backup

launch_id = uuid.uuid4()


def start_metrics_server() -> None:
    logging.info("Starting metrics server")

    start_http_server(8080)

    logging.info("Metrics server started")


def start_scheduler() -> None:
    logging.info("Starting scheduler")

    scheduler = BackgroundScheduler()
    trigger = CronTrigger(hour=22, minute=30, second=0, timezone="UTC")
    scheduler.add_job(order_book_table_truncate_and_backup, trigger=trigger)
    scheduler.start()

    logging.info("Scheduler started")


async def main() -> None:
    tasks = [
        asyncio.create_task(fill_missed_liquidity_intervals()),
        asyncio.create_task(start_collectors()),
    ]

    await asyncio.gather(*tasks)


async def start_collectors() -> None:
    logging.info("Starting data collection")
    logging.info(f"Launch ID: {launch_id}")

    tasks = []  # List to store tasks
    pairs = []  # List to store pairs

    async with get_async_db() as session:
        pairs = await find_all_pairs(session)

    messenger = DiscordMessenger()

    for pair in pairs:
        collector = BinanceExchangeCollector(
            launch_id=launch_id,
            pair_id=pair.id,
            exchange_id=pair.exchange_id,
            symbol=pair.symbol,
            delimiter=pair.delimiter,
            messenger=messenger,
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
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nInterrupted. Closing application...")
    except Exception as e:
        logging.exception(e)
        logging.info("Closing application...")
