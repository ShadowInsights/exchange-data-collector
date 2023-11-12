from abc import ABC, abstractmethod
from typing import Dict

from _decimal import Decimal

from app.common.config import settings
from app.common.processor import Processor
from app.utils.time_utils import (LONDON_TRADING_SESSION,
                                  NEW_YORK_TRADING_SESSION,
                                  TOKYO_TRADING_SESSION,
                                  is_current_time_inside_trading_sessions)

trading_sessions = [
    TOKYO_TRADING_SESSION,
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
]


class Worker(ABC):
    def __init__(self, processor: Processor):
        self._processor = processor

    async def run(self) -> None:
        if (
            settings.IS_TRADING_SESSION_VERIFICATION_REQUIRED
            and not is_current_time_inside_trading_sessions(trading_sessions)
        ):
            return
        else:
            await self._run_worker()

    @abstractmethod
    async def _run_worker(self) -> None:
        pass

    @staticmethod
    def group_order_book(
        order_book: Dict[Decimal, Decimal], delimiter: Decimal
    ) -> Dict[Decimal, Decimal]:
        grouped_order_book = {}
        for price, quantity in order_book.items():
            # Calculate bucketed price
            bucketed_price = price - (price % delimiter)

            # Initialize the bucket if it doesn't exist
            if bucketed_price not in grouped_order_book:
                grouped_order_book[bucketed_price] = Decimal(0.0)

            # Accumulate quantity in the bucket
            grouped_order_book[bucketed_price] += quantity

        return grouped_order_book
