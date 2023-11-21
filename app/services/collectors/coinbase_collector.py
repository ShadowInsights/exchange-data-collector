from typing import AsyncGenerator
from uuid import UUID

from _decimal import Decimal

from app.services.collectors.clients.coinbase_websocket_client import \
    CoinbaseWebsocketClient
from app.services.collectors.clients.schemas.common import OrderBookEvent
from app.services.collectors.common import Collector


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

    async def _broadcast_stream(self) -> AsyncGenerator[OrderBookEvent, None]:
        async for event in self._ws_client.listen_depth_stream():
            yield event
