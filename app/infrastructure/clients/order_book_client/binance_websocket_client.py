import json
from typing import AsyncGenerator

import websockets
from _decimal import Decimal

from app.infrastructure.clients.common import WebsocketClient
from app.infrastructure.clients.order_book_client.schemas.binance import \
    BinanceOrderBookDepthUpdate


class BinanceWebsocketClient(WebsocketClient):
    def __init__(self, symbol: str):
        super().__init__(symbol=symbol, symbol_splitter="")
        self.uri = (
            f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@depth"
        )

    async def listen_depth_stream(
        self,
    ) -> AsyncGenerator[BinanceOrderBookDepthUpdate, None]:
        async with websockets.connect(self.uri) as websocket:
            async for message in websocket:
                data = json.loads(message)
                bids = {Decimal(bid[0]): Decimal(bid[1]) for bid in data["b"]}
                asks = {Decimal(ask[0]): Decimal(ask[1]) for ask in data["a"]}
                yield BinanceOrderBookDepthUpdate(
                    b=bids,
                    a=asks,
                    event_time=data["E"],
                    first_update_id=data["U"],
                    final_update_id=data["u"],
                )
