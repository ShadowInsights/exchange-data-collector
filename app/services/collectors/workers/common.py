import asyncio
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict

from app.common.config import settings
from app.services.collectors.common import trading_sessions
from app.utils.time_utils import is_current_time_inside_trading_sessions


class Worker(ABC):
    async def run(self) -> None:
        if (
            not is_current_time_inside_trading_sessions(trading_sessions)
            and not settings.PYTHON_ENV == "DEV"
        ):
            return
        else:
            await self._run_worker()

    @abstractmethod
    def _run_worker(self) -> None:
        pass

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


def set_interval(seconds) -> callable:
    def decorator(func):
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    await asyncio.sleep(seconds)
                    await func(*args, **kwargs)
                except Exception as e:
                    logging.exception(e)

        return wrapper

    return decorator
