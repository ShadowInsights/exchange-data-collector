import httpx

from app.services.clients.schemas.binance import (OrderBookEntry,
                                                  OrderBookSnapshot)


class BinanceHttpClient:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.http_client = httpx.AsyncClient()
        self.fetch_order_book_snapshot_url = f"https://api.binance.com/api/v3/depth?symbol={self.symbol}&limit=1000"

    async def fetch_order_book_snapshot(self) -> OrderBookSnapshot:
        resp = await self.http_client.get(self.fetch_order_book_snapshot_url)
        data = resp.json()
        bids = [OrderBookEntry(*bid) for bid in data["bids"]]
        asks = [OrderBookEntry(*ask) for ask in data["asks"]]
        return OrderBookSnapshot(data["lastUpdateId"], bids, asks)
