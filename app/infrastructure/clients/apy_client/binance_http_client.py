import logging

import httpx

from app.infrastructure.clients.apy_client.schemas.binance import \
    BinanceAPYSnapshot
from app.infrastructure.clients.common import HttpClient


class BinanceHttpClient(HttpClient):
    def __init__(self, symbol: str):
        super().__init__(symbol=symbol, symbol_splitter="")
        self.fetch_apy_snapshot_url = (
            f"https://www.binance.com/bapi/earn/v1/friendly/finance-earn/simple"
            f"/product/simpleEarnProducts?asset={self.symbol}"
        )
        self.http_client = httpx.AsyncClient()

    async def fetch_apy_snapshot(
        self,
    ) -> BinanceAPYSnapshot | None:
        resp = await self.http_client.get(self.fetch_apy_snapshot_url)
        data = resp.json()

        if data["code"] == -1121:
            logging.info(
                f"Binance exchange doesn't support currency symbol [{self.symbol}]. "
                f"Closing websocket connection"
            )

        apy = data["data"]["list"][0]["highestApy"]

        return BinanceAPYSnapshot(
            apy=apy,
        )
