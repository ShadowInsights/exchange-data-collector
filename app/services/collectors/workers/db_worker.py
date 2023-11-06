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
from app.services.collectors.workers.common import Worker
from app.utils.scheduling_utils import set_interval


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
    async def run(self, *args, **kwargs) -> None:
        await super().run(*args, **kwargs)

    async def _run_worker(self, *args, **kwargs) -> None:
        asyncio.create_task(self.__db_worker(*args, **kwargs))

    async def __db_worker(self, *args, **kwargs) -> None:
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

        callback_event = kwargs.get('callback_event')
        callback_event.set()

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
