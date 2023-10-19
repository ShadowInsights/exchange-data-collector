import asyncio
import logging
from decimal import Decimal
from typing import Dict
from uuid import UUID

from app.services.clients.binance_http_client import BinanceHttpClient
from app.services.clients.binance_websocket_client import \
    BinanceWebsocketClient
from app.services.clients.schemas.binance import (OrderBookEntry,
                                                  OrderBookSnapshot)
from app.services.collectors.common import Collector
from app.services.collectors.workers.common import Worker
from app.services.collectors.workers.db_worker import DbWorker
from app.services.collectors.workers.liquidity_worker import LiquidityWorker
from app.services.collectors.workers.orders_worker import OrdersWorker
from app.services.messengers.liquidity_discord_messenger import \
    LiquidityDiscordMessenger
from app.services.messengers.order_book_discord_messenger import \
    OrderBookDiscordMessenger
from app.utils.math_utils import recalculate_round_average


class BinanceExchangeCollector(Collector):
    def __init__(
        self,
        launch_id: UUID,
        pair_id: UUID,
        exchange_id: UUID,
        symbol: str,
        delimiter: Decimal,
    ):
        super().__init__(
            launch_id,
            pair_id,
            exchange_id,
            symbol,
            delimiter,
        )
        self._http_client = BinanceHttpClient(symbol)
        self._ws_client = BinanceWebsocketClient(symbol)
        self._workers: list[Worker] = [
            DbWorker(self),
            LiquidityWorker(
                collector=self, discord_messenger=LiquidityDiscordMessenger()
            ),
            OrdersWorker(
                collector=self,
                discord_messenger=OrderBookDiscordMessenger(),
            ),
        ]

    async def run(self):
        logging.info(f"Collecting data for {self.symbol}")

        # Open the stream and start the generator for the stream events
        event_generator = self._ws_client.listen_depth_stream()

        # Fetch the initial snapshot
        snapshot = await self._http_client.fetch_order_book_snapshot()
        self.order_book = OrderBookSnapshot(
            snapshot.lastUpdateId,
            {bid.price: bid.quantity for bid in snapshot.bids},
            {ask.price: ask.quantity for ask in snapshot.asks},
        )
        last_update_id = self.order_book.lastUpdateId

        # Init average volume of order books
        self._update_avg_volume()

        logging.info(
            f"Initial snapshot saved with lastUpdateId {last_update_id} [symbol={self.symbol}]"
        )

        for worker in self._workers:
            asyncio.create_task(worker.run())

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

            # Update the local order book with the event data
            for bid in update_event.bids:
                self._update_order_book(self.order_book.bids, bid)
            for ask in update_event.asks:
                self._update_order_book(self.order_book.asks, ask)

            # Update average volume of order books
            self._update_avg_volume()

    def _update_order_book(
        self, order_book: Dict[str, str], update: OrderBookEntry
    ) -> None:
        logging.debug(f"Updating order book with {update}")
        # The data in each event is the absolute quantity for a price level
        price, quantity = update.price, update.quantity
        if quantity == "0.00000000":
            # If the quantity is 0, remove the price level
            order_book.pop(price, None)  # No error if the price is not found
        else:
            # Otherwise, update the quantity at this price level
            order_book[price] = quantity

    def _update_avg_volume(self) -> None:
        logging.debug("Updating average volume")

        self.volume_counter += 1

        total_volume = 0

        # Concat bids with asks and calculate total volume of order_book
        for price, quantity in {
            **self.order_book.asks,
            **self.order_book.bids,
        }.items():
            total_volume += float(price) * float(quantity)

        # Set new average volume
        self.avg_volume = recalculate_round_average(
            avg=self.avg_volume,
            counter=self.volume_counter,
            value=total_volume,
        )

        logging.debug(
            f"Total volume of update №{self.volume_counter}  - {total_volume}"
        )
        logging.debug(f"New average volume is {self.avg_volume}")
