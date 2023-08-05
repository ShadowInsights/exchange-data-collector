import asyncio
import json
import logging
from decimal import Decimal
from typing import Dict

from clickhouse_driver import Client

from app.common.config import settings
from app.services.clients.binance_http_client import BinanceHttpClient
from app.services.clients.binance_websocket_client import \
    BinanceWebsocketClient
from app.services.clients.schemas.binance import OrderBookSnapshot


def handle_decimal_type(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


class BinanceExchangeCollector:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.http_client = BinanceHttpClient(symbol)
        self.ws_client = BinanceWebsocketClient(symbol)
        self.ch_client = Client(
            host=settings.CLICKHOUSE_HOST, port=settings.CLICKHOUSE_PORT
        )
        self.order_book = OrderBookSnapshot(0, {}, {})

    async def collect(self):
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

        # Start the worker task
        delimiter = Decimal(0.01)  # replace with the desired delimiter
        asyncio.create_task(self.worker(delimiter))

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

    async def worker(self, delimiter: Decimal):
        while True:
            grouped_bids = self._group_order_book(
                self.order_book.bids, delimiter)
            grouped_asks = self._group_order_book(
                self.order_book.asks, delimiter)

            # Convert keys and values to string before dumping to json
            grouped_bids = {handle_decimal_type(k): handle_decimal_type(
                v) for k, v in grouped_bids.items()}
            grouped_asks = {handle_decimal_type(k): handle_decimal_type(
                v) for k, v in grouped_asks.items()}

            order_book_json = json.dumps(
                {"asks": grouped_bids, "bids": grouped_asks})
            logging.info(f"Grouped order book: {order_book_json}")
            await asyncio.sleep(10)

    @staticmethod
    def _group_order_book(
        order_book: Dict[str, str], delimiter: Decimal
    ) -> Dict[Decimal, Decimal]:
        grouped_order_book = {}
        for price, quantity in order_book.items():
            price = Decimal(price)
            quantity = Decimal(quantity)
           
            # Calculate bucketed price
            bucketed_price = Decimal(f"0.{price // delimiter}")
            # TODO: fix rounding
            print(price, bucketed_price)
            if bucketed_price not in grouped_order_book:
                grouped_order_book[bucketed_price] = Decimal(0.0)

            # Accumulate quantity in the bucket
            grouped_order_book[bucketed_price] += quantity

        return grouped_order_book

    @staticmethod
    def _update_order_book(order_book: Dict[str, str], update: Dict[str, str]):
        logging.debug(f"Updating order book with {update}")
        # The data in each event is the absolute quantity for a price level
        price, quantity = update.price, update.quantity
        if quantity == "0.00000000":
            # If the quantity is 0, remove the price level
            order_book.pop(price, None)  # No error if the price is not found
        else:
            # Otherwise, update the quantity at this price level
            order_book[price] = quantity
