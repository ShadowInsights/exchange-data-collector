import logging

import httpx
from _decimal import Decimal

from app.services.collectors.clients.common import HttpClient
from app.services.collectors.clients.schemas.binance import \
    BinanceOrderBookSnapshot


class BinanceHttpClient(HttpClient):
    def __init__(self, symbol: str):
        super().__init__(symbol=symbol, symbol_splitter="")
        self.fetch_order_book_snapshot_url = f"https://api.binance.com/api/v3/depth?symbol={self.symbol}&limit=1000"
        self.http_client = httpx.AsyncClient()

    async def fetch_order_book_snapshot(
        self,
    ) -> BinanceOrderBookSnapshot | None:
        resp = await self.http_client.get(self.fetch_order_book_snapshot_url)
        data = resp.json()

        if "code" in data and data["code"] == -1121:
            logging.info(
                f"Binance exchange doesn't support currency pair [{self.symbol}]. "
                f"Closing websocket connection"
            )

            return None

        bids = {Decimal(bid[0]): Decimal(bid[1]) for bid in data["bids"]}
        asks = {Decimal(ask[0]): Decimal(ask[1]) for ask in data["asks"]}
        return BinanceOrderBookSnapshot(
            last_update_id=data["lastUpdateId"],
            b=bids,
            a=asks,
        )
