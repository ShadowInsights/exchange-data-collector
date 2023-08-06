import asyncio
from datetime import datetime
import json
import logging
import uuid
from decimal import Decimal
from typing import Dict
from datetime import datetime
from pytz import utc

from click import UUID
from clickhouse_driver import Client

from app.common.config import BINANCE_PAIRS, EXCHANGES
from app.db.models.binance_order import BinanceOrderModel
from app.db.repositories.binance_order_repository import ClickHouseRepository
from app.services.clients.binance_http_client import BinanceHttpClient
from app.services.clients.binance_websocket_client import \
    BinanceWebsocketClient
from app.services.clients.schemas.binance import OrderBookSnapshot

EXCHANGE_ID = EXCHANGES["Binance"]


def handle_decimal_type(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


class BinanceExchangeCollector:
    def __init__(
        self,
        launch_id: UUID,
        symbol: str,
        delimiter: Decimal,
        ch_client: Client,
    ):
        self.launch_id = launch_id
        self.symbol = symbol
        self.delimiter = delimiter
        self.http_client = BinanceHttpClient(symbol)
        self.ws_client = BinanceWebsocketClient(symbol)
        self.ch_repository = ClickHouseRepository(ch_client)
        self.order_book = OrderBookSnapshot(0, {}, {})
        self.stamp_id = 0
        self.pair_id = BINANCE_PAIRS[self.symbol]

    async def run(self):
        logging.info(f"Collecting data for {self.symbol}")

        # Open the stream and start the generator for the stream events
        event_generator = self.ws_client.listen_depth_stream()

        # Fetch the initial snapshot
        snapshot = await self.http_client.fetch_order_book_snapshot()
        self.order_book = OrderBookSnapshot(
            snapshot.lastUpdateId,
            {bid.price: bid.quantity for bid in snapshot.bids},
            {ask.price: ask.quantity for ask in snapshot.asks},
        )
        last_update_id = self.order_book.lastUpdateId

        logging.info(
            f"Initial snapshot saved with lastUpdateId {last_update_id}"
        )

        asyncio.create_task(self.worker())

        # Process the buffered and incoming stream events
        async for update_event in event_generator:
            logging.debug(f"Processing update event {update_event}")

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

    async def worker(self):
        while True:
            start_time = datetime.now()
            try:
                # Prepare
                bucket_id = uuid.uuid4()
                create_at = datetime.now(utc)

                # Group the order book by bucket
                grouped_bids = self._group_order_book(
                    self.order_book.bids, self.delimiter
                )
                grouped_asks = self._group_order_book(
                    self.order_book.asks, self.delimiter
                )

                # Build the order models
                bids = self._build_binance_order_models(
                    grouped_bids, 0, bucket_id, create_at
                )
                asks = self._build_binance_order_models(
                    grouped_asks, 1, bucket_id, create_at
                )
                # Save the bucket to ClickHouse
                await self.ch_repository.save_bucket(bids + asks)

                # Increment the stamp_id
                self.stamp_id += 1

                # Log the order book
                self._log_order_book(grouped_bids, grouped_asks)
            except Exception as e:
                logging.error(f"Error: {e}")

            # Calculate the time spent
            time_spent = datetime.now() - start_time
            time_spent = time_spent.total_seconds()
            logging.info(f"Worker function took {time_spent} seconds")

            # If the work takes less than 10 seconds, sleep for the remainder
            if time_spent < 10:
                await asyncio.sleep(10 - time_spent)
            # If it takes more, log and start again immediately
            else:
                logging.warn(
                    f"Worker function took longer than 1 seconds: {time_spent}")

    # TODO: Fix this function
    def _group_order_book(
        self, order_book: Dict[str, str], delimiter: Decimal
    ) -> Dict[Decimal, Decimal]:
        grouped_order_book = {}
        for price, quantity in order_book.items():
            price = Decimal(price)
            quantity = Decimal(quantity)

            # Calculate bucketed price
            bucketed_price = Decimal(f"0.{price // delimiter}")

            if bucketed_price not in grouped_order_book:
                grouped_order_book[bucketed_price] = Decimal(0.0)

            # Accumulate quantity in the bucket
            grouped_order_book[bucketed_price] += quantity

        return grouped_order_book

    def _update_order_book(
        self, order_book: Dict[str, str], update: Dict[str, str]
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

    def _build_binance_order_models(
        self, order_book: Dict[str, str], order_type: str, bucket_id: UUID, create_at: datetime
    ) -> list[BinanceOrderModel]:
        return [
            BinanceOrderModel(
                id=uuid.uuid4(),
                launch_id=self.launch_id,
                order_type=order_type,
                price=Decimal(price),
                quantity=Decimal(quantity),
                bucket_id=bucket_id,
                pair_id=self.pair_id,
                exchange_id=EXCHANGE_ID,
                stamp_id=self.stamp_id,
                created_at=create_at
            )
            for price, quantity in order_book.items()
        ]

    def _log_order_book(self, grouped_bids, grouped_asks) -> None:
        # Convert keys and values to string before dumping to json
        grouped_bids = {
            handle_decimal_type(k): handle_decimal_type(v)
            for k, v in grouped_bids.items()
        }
        grouped_asks = {
            handle_decimal_type(k): handle_decimal_type(v)
            for k, v in grouped_asks.items()
        }

        order_book_json = json.dumps(
            {"asks": grouped_bids, "bids": grouped_asks}
        )
        logging.info(f"Saved grouped order book: {order_book_json}")
