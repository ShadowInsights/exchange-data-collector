import logging
from uuid import UUID

from _decimal import Decimal

from app.services.collectors.clients.schemas.common import (EventTypeEnum,
                                                            OrderBook,
                                                            OrderBookEvent)
from app.services.collectors.common import Collector
from app.utils.event_utils import EventHandler


class Processor:
    def __init__(
        self,
        launch_id: UUID,
        pair_id: UUID,
        collector: Collector,
        event_handler: EventHandler,
        symbol: str,
        delimiter: Decimal,
    ):
        self._collector = collector
        self._symbol = symbol
        self._delimiter = delimiter
        self._pair_id = pair_id
        self._launch_id = launch_id
        self._order_book = OrderBook(a={}, b={})
        self.event_handler = event_handler

    async def run(self):
        # Open the stream and start the generator for the stream events
        event_generator = self._collector.listen_stream()

        async for event in event_generator:
            if event is None:
                continue

            match event.event_type:
                case EventTypeEnum.INIT:
                    self._init_order_book(snapshot=event)

                    self.event_handler.emit(EventTypeEnum.INIT.value)
                case EventTypeEnum.UPDATE:
                    self._update_order_book(update_event=event)

                    self.event_handler.emit(EventTypeEnum.UPDATE.value)
                case _:
                    logging.warning(f"Unrecognised error event {event}")

    def _init_order_book(self, snapshot: OrderBookEvent):
        logging.debug(
            f"Processing init event {snapshot} [symbol={self.symbol}]"
        )

        self.order_book.a, self.order_book.b = snapshot.a, snapshot.b

        logging.info(f"Initial snapshot saved [symbol={self.symbol}]")

    def _update_order_book(self, update_event: OrderBookEvent):
        logging.debug(
            f"Processing update event {update_event} [symbol={self.symbol}]"
        )

        # Update the local order book with the event data
        for bid in update_event.b.items():
            self.__update_order_book(self.order_book.b, bid)
        for ask in update_event.a.items():
            self.__update_order_book(self.order_book.a, ask)

    def __update_order_book(
        self,
        order_book: dict[Decimal, Decimal],
        update: tuple[Decimal, Decimal],
    ) -> None:
        logging.debug(f"Updating order book with {update}")

        price = update[0]
        quantity = update[1]

        # The data in each event is the absolute quantity for a price level
        if price * quantity == 0.0:
            # If the quantity is 0, remove the price level
            order_book.pop(price, None)  # No error if the price is not found
        else:
            # Otherwise, update the quantity at this price level
            order_book[price] = quantity

    @property
    def order_book(self):
        return self._order_book

    @property
    def collector(self):
        return self._collector

    @property
    def delimiter(self):
        return self._delimiter

    @property
    def pair_id(self):
        return self._pair_id

    @property
    def launch_id(self):
        return self._launch_id

    @property
    def symbol(self):
        return self._symbol
