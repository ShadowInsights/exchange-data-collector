from abc import ABC
from decimal import Decimal
import logging
from uuid import UUID

from pydantic import BaseModel

from app.services.clients.schemas.binance import OrderBookSnapshot
from app.services.messengers.base_messenger import BaseMessenger
from app.utils.time_utils import (LONDON_TRADING_SESSION,
                                  NEW_YORK_TRADING_SESSION,
                                  TOKYO_TRADING_SESSION)

trading_sessions = [
    TOKYO_TRADING_SESSION,
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
]


class OrderBook(BaseModel):
    a: dict[Decimal, Decimal]
    b: dict[Decimal, Decimal]


class Collector(ABC):
    def __init__(
        self,
        launch_id: UUID,
        pair_id: UUID,
        exchange_id: UUID,
        symbol: str,
        delimiter: Decimal,
        messenger: BaseMessenger,
    ):
        # TODO: make protected
        self.order_book = OrderBookSnapshot(0, {}, {})
        self.launch_id = launch_id
        self.pair_id = pair_id
        self.symbol = symbol
        self.delimiter = delimiter
        self.avg_volume = 0
        self.volume_counter = 0
        self.messenger = messenger
        self._exchange_id = exchange_id

    def clear_volume_stats(self):
        logging.debug("Cleaning volume stats")

        self.avg_volume = 0
        self.volume_counter = 0
