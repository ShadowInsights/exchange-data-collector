import json
from typing import AsyncGenerator

import websockets

from app.services.clients.schemas.binance import (DepthUpdateEvent,
                                                  OrderBookEntry)


class BinanceWebsocketClient:
    def __init__(self, symbol: str):
        self.symbol = symbol.lower()
        self.uri = f"wss://stream.binance.com:9443/ws/{self.symbol}@depth"

    async def listen_depth_stream(
        self,
    ) -> AsyncGenerator[DepthUpdateEvent, None]:
        async with websockets.connect(self.uri) as websocket:
            async for message in websocket:
                data = json.loads(message)
                bids = [OrderBookEntry(*bid) for bid in data["b"]]
                asks = [OrderBookEntry(*ask) for ask in data["a"]]
                yield DepthUpdateEvent(
                    data["e"],
                    data["E"],
                    data["s"],
                    data["U"],
                    data["u"],
                    bids,
                    asks,
                )
