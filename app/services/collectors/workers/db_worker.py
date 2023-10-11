import asyncio
import copy
import json
import logging
from datetime import datetime
from decimal import Decimal

from app.common.config import settings
from app.common.database import get_async_db
from app.db.repositories.order_book_repository import create_order_book
from app.services.collectors.common import Collector, OrderBook
from app.services.collectors.workers.common import Worker, set_interval


def handle_decimal_type(obj) -> str:
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


class DbWorker(Worker):
    # TODO: Create a base class for all collectors
    def __init__(self, collector: Collector):
        self._collector = collector
        self._stamp_id = 0

    @set_interval(settings.DB_WORKER_JOB_INTERVAL)
    async def run(self) -> None:
        await super().run()

    async def _run_worker(self) -> None:
        asyncio.create_task(self.__db_worker())

    async def __db_worker(self) -> None:
        start_time = datetime.now()
        logging.debug(
            f"Worker function cycle started [symbol={self._collector.symbol}]"
        )

        collector_current_order_book = copy.deepcopy(
            self._collector.order_book
        )
        order_book = OrderBook(
            a=self.group_order_book(
                collector_current_order_book.asks, self._collector.delimiter
            ),
            b=self.group_order_book(
                collector_current_order_book.bids, self._collector.delimiter
            ),
        )
        try:
            async with get_async_db() as session:
                await create_order_book(
                    session,
                    self._collector.launch_id,
                    self._stamp_id,
                    self._collector.pair_id,
                    order_book=order_book.model_dump_json(),
                )

            # Increment the stamp_id
            self._stamp_id += 1

            # Log the order book
            self.__log_order_book(order_book.b, order_book.a)
        except Exception as e:
            logging.error(f"Error: {e} [symbol={self._collector.symbol}]")

        # Calculate the time spent
        time_spent = datetime.now() - start_time
        time_spent = time_spent.total_seconds()
        logging.debug(
            f"Worker function took {time_spent} seconds [symbol={self._collector.symbol}]"
        )

        # If the work takes less than 1 seconds, sleep for the remainder
        if time_spent < 1:
            await asyncio.sleep(1 - time_spent)
        # If it takes more, log and start again immediately
        else:
            logging.warn(
                f"Worker function took longer than 1 seconds: {time_spent} seconds [symbol={self._collector.symbol}]"
            )

    def __log_order_book(self, grouped_bids, grouped_asks) -> None:
        # Convert keys and values to string before dumping to json
        grouped_bids = {
            handle_decimal_type(k): handle_decimal_type(v)
            for k, v in grouped_bids.items()
        }
        grouped_asks = {
            handle_decimal_type(k): handle_decimal_type(v)
            for k, v in grouped_asks.items()
        }

        order_book_json = json.dumps(
            {"asks": grouped_bids, "bids": grouped_asks}
        )
        logging.debug(
            f"Saved grouped order book: {order_book_json} [symbol={self._collector.symbol}]"
        )
