from _decimal import Decimal

from app.services.collectors.clients.schemas.common import (
    OrderBookSnapshot,
    OrderBookUpdate,
)


class BinanceOrderBookSnapshot(OrderBookSnapshot):
    def __init__(
        self,
        last_update_id: int,
        b: dict[Decimal, Decimal],
        a: dict[Decimal, Decimal],
    ):
        super().__init__(b=b, a=a)
        self.last_update_id = last_update_id


class BinanceOrderBookDepthUpdate(OrderBookUpdate):
    def __init__(
        self,
        b: dict[Decimal, Decimal],
        a: dict[Decimal, Decimal],
        event_time: int,
        first_update_id: int,
        final_update_id: int,
    ):
        super().__init__(b=b, a=a)
        self.event_time = event_time
        self.first_update_id = first_update_id
        self.final_update_id = final_update_id
