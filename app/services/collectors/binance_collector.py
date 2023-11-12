import logging
from typing import AsyncGenerator
from uuid import UUID

from _decimal import Decimal

from app.services.collectors.clients.binance_http_client import \
    BinanceHttpClient
from app.services.collectors.clients.binance_websocket_client import \
    BinanceWebsocketClient
from app.services.collectors.clients.schemas.common import OrderBookEvent
from app.services.collectors.common import Collector


class BinanceCollector(Collector):
    def __init__(
        self, launch_id: UUID, pair_id: UUID, symbol: str, delimiter: Decimal
    ):
        super().__init__(
            launch_id=launch_id,
            pair_id=pair_id,
            symbol=symbol,
            delimiter=delimiter,
        )
        self._http_client = BinanceHttpClient(symbol)
        self._ws_client = BinanceWebsocketClient(symbol)

    async def _broadcast_stream(self) -> AsyncGenerator[OrderBookEvent, None]:
        # Open the stream and start the generator for the stream events
        event_generator = self._ws_client.listen_depth_stream()

        # Fetch the initial snapshot from exchange
        snapshot = await self._http_client.fetch_order_book_snapshot()

        if snapshot is None:
            await event_generator.aclose()
            return

        # Handle the initial snapshot
        yield snapshot

        last_update_id = snapshot.last_update_id

        # Process the buffered and incoming stream events
        async for update_event in event_generator:
            logging.debug(
                f"Processing update event {update_event} [symbol={self.symbol}]"
            )

            # Drop any event where u is <= lastUpdateId in the snapshot
            if update_event.final_update_id <= last_update_id:
                continue

            # The first processed event should have U <= lastUpdateId+1 AND u >= lastUpdateId+1
            # After the first update, each new event's U should be equal to the previous event's u+1
            assert (
                last_update_id < update_event.first_update_id
            ), "Update event out of order"
            last_update_id = update_event.final_update_id

            yield update_event
