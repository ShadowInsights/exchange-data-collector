import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator
from uuid import UUID

from _decimal import Decimal

from app.infrastructure.clients.schemas.common import OrderBookEvent


class Collector(ABC):
    def __init__(
        self, launch_id: UUID, pair_id: UUID, symbol: str, delimiter: Decimal
    ):
        self.launch_id = launch_id
        self.pair_id = pair_id
        self.symbol = symbol
        self.delimiter = delimiter
        self.is_interrupted = False

    async def listen_stream(
        self,
    ) -> AsyncGenerator[OrderBookEvent | None, None]:
        logging.info(f"Collecting data for {self.symbol}")

        # Open the stream and start the generator for the stream events
        while self.is_interrupted is not True:
            try:
                async for event in self._broadcast_stream():
                    yield event
            except Exception as err:
                logging.exception(
                    exc_info=err,
                    msg=f"Collector with pair {self.pair_id} will be relaunched",
                )

    @abstractmethod
    async def _broadcast_stream(
        self,
    ) -> AsyncGenerator[OrderBookEvent | None, None]:
        yield None
