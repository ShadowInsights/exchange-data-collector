import copy
import logging
from decimal import Decimal
from typing import Dict, Literal

from app.common.config import settings
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector
from app.services.collectors.common import OrderBook
from app.services.collectors.workers.common import Worker, set_interval
from app.utils.time_utils import get_current_time


class OrdersWorker(Worker):
    def __init__(self, collector: BinanceExchangeCollector):
        self._collector = collector
        self._previous_order_book: OrderBook = None
        self._detected_anomalies: Dict[Decimal, float] = {}

    @set_interval(settings.ORDERS_WORKER_JOB_INTERVAL)
    async def run(self) -> None:
        await super().run()

    async def _run_worker(self) -> None:
        self.__process_orders()

    def __process_orders(self) -> None:
        logging.debug(
            f"Orders processing cycle started [symbol={self._collector.symbol}]"
        )

        collector_current_order_book = copy.deepcopy(
            self._collector.order_book
        )

        if self._previous_order_book is None:
            self._previous_order_book = self.__group_orders(
                collector_current_order_book
            )
            return

        current_order_book = self.__group_orders(collector_current_order_book)

        self.__check_anomalies(current_order_book)

        self._previous_order_book = current_order_book

    def __group_orders(self, order_book: OrderBook) -> OrderBook:
        return OrderBook(
            a=self.group_order_book(order_book.a, self._collector.delimiter),
            b=self.group_order_book(order_book.b, self._collector.delimiter),
        )

    def __check_anomalies(self, order_book: OrderBook) -> None:
        anomaly_asks = self.__get_anomalies(order_book.a, "asks")
        anomaly_bids = self.__get_anomalies(order_book.b, "bids")

        new_anomaly_asks = {
            price
            for price in anomaly_asks.keys()
            if price not in self._detected_anomalies
        }
        new_anomaly_bids = {
            price
            for price in anomaly_bids.keys()
            if price not in self._detected_anomalies
        }

        current_time = get_current_time()

        for price in new_anomaly_asks:
            logging.info(
                f"New anomaly detected in asks [symbol={self._collector.symbol}, "
                f"price={price}, quantity={anomaly_asks[price]}]"
            )
            self._detected_anomalies[price] = current_time

        for price in new_anomaly_bids:
            logging.info(
                f"New anomaly detected in bids [symbol={self._collector.symbol}, "
                f"price={price}, quantity={anomaly_bids[price]}]"
            )
            self._detected_anomalies[price] = current_time

        # Prune old anomalies
        self.__prune_anomalies()

    def __get_anomalies(
        self, orders: Dict[Decimal, Decimal], order_type: Literal["asks", "bids"],
    ) -> Dict[Decimal, Decimal]:
        top_orders = self.__get_top_orders(orders, order_type)

        if not top_orders:
            return {}

        average_top = sum(top_orders.values()) / len(top_orders)

        return {
            price: qty
            for price, qty in top_orders.items()
            if qty > settings.ORDER_ANOMALY_MULTIPLIER * average_top
        }

    def __prune_anomalies(self) -> None:
        """Remove anomalies that have exceeded their TTL."""
        current_time = get_current_time()
        expired_anomalies = [
            price
            for price, detected_time in self._detected_anomalies.items()
            if current_time - detected_time > settings.ANOMALIES_TTL
        ]

        for price in expired_anomalies:
            del self._detected_anomalies[price]

    def __get_top_orders(
        self,
        orders: Dict[Decimal, Decimal],
        order_type: Literal["asks", "bids"],
    ) -> Dict[Decimal, Decimal]:
        if order_type == "asks":
            return dict(
                sorted(orders.items(), key=lambda item: item[0])[
                    : settings.TOP_N_ORDERS
                ]
            )
        elif order_type == "bids":
            return dict(
                sorted(orders.items(), key=lambda item: item[0], reverse=True)[
                    : settings.TOP_N_ORDERS
                ]
            )
        else:
            raise ValueError("Invalid order type")
