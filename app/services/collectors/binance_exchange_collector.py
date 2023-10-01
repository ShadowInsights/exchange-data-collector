import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict
from uuid import UUID

from app.db.common import get_db
from app.db.repositories.order_book_repository import crate_order_book
from app.services.clients.binance_http_client import BinanceHttpClient
from app.services.clients.binance_websocket_client import \
    BinanceWebsocketClient
from app.services.clients.schemas.binance import OrderBookSnapshot
from app.services.collectors.common import OrderBook
from app.services.collectors.workers.db_worker import DbWorker
from app.services.collectors.workers.walls_worker import WallsWorker
from app.utils.time_utils import (LONDON_TRADING_SESSION,
                                  NEW_YORK_TRADING_SESSION,
                                  TOKYO_TRADING_SESSION,
                                  is_current_time_inside_trading_sessions)


def handle_decimal_type(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


trading_sessions = [
    TOKYO_TRADING_SESSION,
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
]


class BinanceExchangeCollector:
    def __init__(
        self,
        launch_id: UUID,
        pair_id: UUID,
        exchange_id: UUID,
        symbol: str,
        delimiter: Decimal,
    ):
        self._launch_id = launch_id
        self._symbol = symbol
        self._delimiter = delimiter
        self._http_client = BinanceHttpClient(symbol)
        self._ws_client = BinanceWebsocketClient(symbol)
        self._order_book = OrderBookSnapshot(0, {}, {})
        self._stamp_id = 0
        self._pair_id = pair_id
        self._exchange_id = exchange_id
        self._workers = [WallsWorker(), DbWorker()]

    async def run(self):
        logging.info(f"Collecting data for {self._symbol}")

        # Open the stream and start the generator for the stream events
        event_generator = self._ws_client.listen_depth_stream()

        # Fetch the initial snapshot
        snapshot = await self._http_client.fetch_order_book_snapshot()
        self._order_book = OrderBookSnapshot(
            snapshot.lastUpdateId,
            {bid.price: bid.quantity for bid in snapshot.bids},
            {ask.price: ask.quantity for ask in snapshot.asks},
        )
        last_update_id = self._order_book.lastUpdateId

        logging.info(
            f"Initial snapshot saved with lastUpdateId {last_update_id} [symbol={self._symbol}]"
        )

        for worker in self._workers:
            asyncio.create_task(worker.run())

        # asyncio.create_task(self.__walls_worker())
        # asyncio.create_task(self.__db_worker())
        # asyncio.create_task(self.__liquidity_worker())

        # Process the buffered and incoming stream events
        async for update_event in event_generator:
            logging.debug(
                f"Processing update event {update_event} [symbol={self._symbol}]"
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
                self._update_order_book(self._order_book.bids, bid)
            for ask in update_event.asks:
                self._update_order_book(self._order_book.asks, ask)

    async def __db_worker(self):
        while True:
            start_time = datetime.now()
            logging.debug(
                f"Worker function cycle started [symbol={self._symbol}]"
            )

            try:
                if not is_current_time_inside_trading_sessions(
                    trading_sessions
                ):
                    await asyncio.sleep(1)
                    continue

                order_book = OrderBook(
                    a=self._group_order_book(
                        self._order_book.asks, self._delimiter
                    ),
                    b=self._group_order_book(
                        self._order_book.bids, self._delimiter
                    ),
                )

                async with get_db() as session:
                    await crate_order_book(
                        session,
                        self._launch_id,
                        self._stamp_id,
                        self._pair_id,
                        order_book=order_book.model_dump_json(),
                    )

                # Increment the stamp_id
                self._stamp_id += 1

                # Log the order book
                self._log_order_book(order_book.b, order_book.a)
            except Exception as e:
                logging.error(f"Error: {e} [symbol={self._symbol}]")

            # Calculate the time spent
            time_spent = datetime.now() - start_time
            time_spent = time_spent.total_seconds()
            logging.debug(
                f"Worker function took {time_spent} seconds [symbol={self._symbol}]"
            )

            # If the work takes less than 1 seconds, sleep for the remainder
            if time_spent < 1:
                await asyncio.sleep(1 - time_spent)
            # If it takes more, log and start again immediately
            else:
                logging.warn(
                    f"Worker function took longer than 1 seconds: {time_spent} seconds [symbol={self._symbol}]"
                )

    def _group_order_book(
        self, order_book: Dict[str, str], delimiter: Decimal
    ) -> Dict[Decimal, Decimal]:
        grouped_order_book = {}
        for price, quantity in order_book.items():
            price = Decimal(price)
            quantity = Decimal(quantity)

            # Calculate bucketed price
            bucketed_price = price - (price % delimiter)

            # Initialize the bucket if it doesn't exist
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
        logging.debug(
            f"Saved grouped order book: {order_book_json} [symbol={self._symbol}]"
        )
