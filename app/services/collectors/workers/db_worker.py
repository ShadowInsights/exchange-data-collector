import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict

from app.common.database import get_async_db
from app.db.repositories.order_book_repository import create_order_book
from app.services.collectors.common import OrderBook
from app.utils.time_utils import (LONDON_TRADING_SESSION,
                                  NEW_YORK_TRADING_SESSION,
                                  TOKYO_TRADING_SESSION,
                                  is_current_time_inside_trading_sessions)

trading_sessions = [
    TOKYO_TRADING_SESSION,
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
]


def set_interval(seconds):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            while True:
                await asyncio.sleep(seconds)
                await func(*args, **kwargs)

        return wrapper

    return decorator


def handle_decimal_type(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


class Worker(ABC):
    @abstractmethod
    async def run(self):
        pass


class DbWorker(Worker):
    def __init__(self, collector):
        self._collector = collector
        self._stamp_id = 0

    @set_interval(5)
    async def run(self):
        asyncio.create_task(self.__db_worker())

    async def __db_worker(self):
        # if not is_current_time_inside_trading_sessions(
        #         trading_sessions
        # ):
        #     return

        start_time = datetime.now()
        logging.debug(
            f"Worker function cycle started [symbol={self._collector.symbol}]"
        )

        try:
            order_book = OrderBook(
                a=self.group_order_book(
                    self._collector.order_book.asks, self._collector.delimiter
                ),
                b=self.group_order_book(
                    self._collector.order_book.asks, self._collector.delimiter
                ),
            )

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
            self._log_order_book(order_book.b, order_book.a)
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

    def _log_order_book(self, grouped_bids, grouped_asks) -> None:
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

    @staticmethod
    def group_order_book(
        order_book: Dict[str, str], delimiter: Decimal
    ) -> Dict[Decimal, Decimal]:
        grouped_order_book = {}
        for price, quantity in order_book.items():
            price = Decimal(price)
            quantity = Decimal(quantity)

            # Calculate bucketed price
            bucketed_price = price - (price % delimiter)

            # Initialize the bucket if it doesn't exist
            if bucketed_price not in grouped_order_book:
                grouped_order_book[bucketed_price] = Decimal(0.0)

            # Accumulate quantity in the bucket
            grouped_order_book[bucketed_price] += quantity

        return grouped_order_book
