import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict

from _decimal import Decimal

from app.application.common.processor import Processor
from app.config import settings
from app.utilities.time_utils import (
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
    TOKYO_TRADING_SESSION,
    is_current_time_inside_trading_sessions,
)

trading_sessions = [
    TOKYO_TRADING_SESSION,
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
]


class Worker(ABC):
    def __init__(
        self,
        processor: Processor,
        is_trading_session_verification_required: bool = settings.IS_TRADING_SESSION_VERIFICATION_REQUIRED,
    ):
        self._processor = processor
        self._is_trading_session_verification_required = (
            is_trading_session_verification_required
        )

    async def run(self, callback_event: asyncio.Event | None = None) -> None:
        try:
            if (
                self._is_trading_session_verification_required
                and not is_current_time_inside_trading_sessions(
                    trading_sessions
                )
            ):
                return
            else:
                await self._run_worker(callback_event)
        except Exception as err:
            logging.exception(exc_info=err, msg="Error occurred")

    @abstractmethod
    async def _run_worker(
        self, callback_event: asyncio.Event | None = None
    ) -> None:
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
