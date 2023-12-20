from typing import AsyncGenerator
from uuid import UUID

from _decimal import Decimal

from app.application.common.collector import Collector
from app.infrastructure.clients.coinbase_websocket_client import (
    CoinbaseWebsocketClient,
)
from app.infrastructure.clients.schemas.common import OrderBookEvent


class CoinbaseCollector(Collector):
    def __init__(
        self, launch_id: UUID, pair_id: UUID, symbol: str, delimiter: Decimal
    ):
        super().__init__(
            launch_id=launch_id,
            pair_id=pair_id,
            symbol=symbol,
            delimiter=delimiter,
        )
        self._ws_client = CoinbaseWebsocketClient(symbol=symbol)

    async def _broadcast_stream(
        self,
    ) -> AsyncGenerator[OrderBookEvent | None, None]:
        async for event in self._ws_client.listen_depth_stream():
            yield event
