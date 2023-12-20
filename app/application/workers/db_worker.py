import asyncio
import copy
import json
import logging
from dataclasses import asdict, dataclass

from _decimal import Decimal

from app.application.common.processor import Processor
from app.application.workers.common import Worker
from app.config import settings
from app.infrastructure.clients.schemas.common import OrderBook
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.repositories.order_book_repository import (
    create_order_book,
)
from app.utilities.scheduling_utils import SetInterval


@dataclass
class OrderBookJson:
    a: dict[str, str]
    b: dict[str, str]


def handle_decimal_type(obj: Decimal | float | int) -> str:
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


class DbWorker(Worker):
    def __init__(self, processor: Processor) -> None:
        super().__init__(processor)
        self._stamp_id = 0

    @SetInterval(settings.DB_WORKER_JOB_INTERVAL, name="DB worker")
    async def run(self, callback_event: asyncio.Event) -> None:
        await super().run(callback_event)
        if callback_event:
            callback_event.set()

    async def _run_worker(self, _: asyncio.Event | None = None) -> None:
        await self.__db_worker()

    async def __db_worker(self) -> None:
        collector_current_order_book = copy.deepcopy(
            self._processor.order_book
        )
        order_book = OrderBook(
            a=self.group_order_book(
                collector_current_order_book.a, self._processor.delimiter
            ),
            b=self.group_order_book(
                collector_current_order_book.b, self._processor.delimiter
            ),
        )

        order_book_json = self.__convert_to_json(order_book)

        try:
            async with get_async_db() as session:
                await create_order_book(
                    session,
                    self._processor.launch_id,
                    self._stamp_id,
                    self._processor.pair_id,
                    order_book_json=order_book_json,
                )

            # Increment the stamp_id
            self._stamp_id += 1

            # Log the order book
            logging.debug(
                f"Saved grouped order book [symbol={self._processor.symbol}]"
            )
        except Exception as e:
            logging.error(f"Error: {e} [symbol={self._processor.symbol}]")

    def __convert_to_json(self, order_book: OrderBook) -> str:
        asks = {
            handle_decimal_type(ask[0]): handle_decimal_type(ask[1])
            for ask in order_book.a.items()
        }
        bids = {
            handle_decimal_type(bid[0]): handle_decimal_type(bid[1])
            for bid in order_book.b.items()
        }

        return json.dumps(asdict(OrderBookJson(a=asks, b=bids)))
