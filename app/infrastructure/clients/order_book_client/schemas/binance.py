from app.infrastructure.clients.order_book_client.schemas.common import (
    OrderBookSnapshot, OrderBookUpdate)


class BinanceOrderBookSnapshot(OrderBookSnapshot):
    last_update_id: int


class BinanceOrderBookDepthUpdate(OrderBookUpdate):
    event_time: int
    first_update_id: int
    final_update_id: int

