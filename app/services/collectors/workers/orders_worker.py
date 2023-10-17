import asyncio
import copy
import logging
from decimal import Decimal
from typing import Dict, List, Literal, NamedTuple, Set

from app.common.config import settings
from app.services.clients.schemas.binance import OrderBookSnapshot
from app.services.collectors.common import Collector, OrderBook
from app.services.collectors.workers.common import Worker, set_interval
from app.services.messengers.order_book_discord_messenger import (
    OrderAnomalyNotification, OrderBookDiscordMessenger)
from app.utils.math_utils import calc_avg
from app.utils.time_utils import get_current_time


class OrderAnomaly(NamedTuple):
    price: Decimal
    quantity: Decimal
    order_liquidity: Decimal
    average_liquidity: Decimal
    position: int
    type: Literal["ask", "bid"]


class AnomalyKey(NamedTuple):
    price: Decimal
    type: Literal["ask", "bid"]


class ObservingOrderAnomaly(NamedTuple):
    time: float
    order_anomaly: OrderAnomaly


class OrdersWorker(Worker):
    def __init__(
        self,
        collector: Collector,
        discord_messenger: OrderBookDiscordMessenger,
        order_anomaly_multiplier: float = settings.ORDER_ANOMALY_MULTIPLIER,
        anomalies_detection_ttl: int = settings.ANOMALIES_DETECTION_TTL,
        anomalies_observing_ttl: int = settings.ANOMALIES_OBSERVING_TTL,
        anomalies_observing_ratio: float = settings.ANOMALIES_OBSERVING_RATIO,
        top_n_orders: int = settings.TOP_N_ORDERS,
    ):
        self._collector = collector
        self._discord_messenger = discord_messenger
        self._detected_anomalies: Dict[AnomalyKey, float] = {}
        self._observing_anomalies: Dict[AnomalyKey, ObservingOrderAnomaly] = {}
        self._orders_anomaly_multiplier = Decimal(order_anomaly_multiplier)
        self._anomalies_detection_ttl = anomalies_detection_ttl
        self._anomalies_observing_ttl = anomalies_observing_ttl
        self._anomalies_observing_ratio = Decimal(anomalies_observing_ratio)
        self._top_n_orders = top_n_orders

    @set_interval(settings.ORDERS_WORKER_JOB_INTERVAL)
    async def run(self) -> None:
        await super().run()

    async def _run_worker(self) -> None:
        await self.__process_orders()

    async def __process_orders(self) -> None:
        logging.debug(
            f"Orders processing cycle started [symbol={self._collector.symbol}]"
        )
        current_order_book = self.__group_orders(
            copy.deepcopy(self._collector.order_book)
        )
        anomalies = self.__find_anomalies(current_order_book)
        filtered_anomalies = self.__filter_anomalies(anomalies)

        if filtered_anomalies:
            order_anomaly_notifications = [
                OrderAnomalyNotification(
                    price=anomaly.price,
                    quantity=anomaly.quantity,
                    order_liquidity=anomaly.order_liquidity,
                    average_liquidity=anomaly.average_liquidity,
                    type=anomaly.type,
                )
                for anomaly in filtered_anomalies
            ]
            asyncio.create_task(
                self._discord_messenger.send_notifications(
                    order_anomaly_notifications,
                    self._collector.pair_id,
                )
            )

    def __group_orders(self, order_book: OrderBookSnapshot) -> OrderBook:
        return OrderBook(
            a=self.group_order_book(
                order_book.asks, self._collector.delimiter
            ),
            b=self.group_order_book(
                order_book.bids, self._collector.delimiter
            ),
        )

    def __find_anomalies(self, order_book: OrderBook) -> List[OrderAnomaly]:
        return self.__get_anomalies(
            order_book.a, "ask"
        ) + self.__get_anomalies(order_book.b, "bid")

    def __get_anomalies(
        self, orders: Dict[Decimal, Decimal], order_type: Literal["ask", "bid"]
    ) -> List[OrderAnomaly]:
        top_orders = self.__get_sorted_top_orders(orders, order_type)

        if not top_orders:
            return []

        anomalies = []
        for position, (price, qty) in enumerate(top_orders.items()):
            liquidity = price * qty
            avg_liquidity = calc_avg(
                [p * q for p, q in top_orders.items() if p != price],
                (len(top_orders) - 1),
            )
            biggest_order = max(
                [p * q for p, q in top_orders.items() if p != price]
            )

            if liquidity > self._orders_anomaly_multiplier * biggest_order:
                anomalies.append(
                    OrderAnomaly(
                        price,
                        qty,
                        liquidity,
                        avg_liquidity,
                        position,
                        order_type,
                    )
                )

        return anomalies

    def __filter_anomalies(
        self, anomalies: List[OrderAnomaly]
    ) -> List[OrderAnomaly]:
        current_time = get_current_time()
        filtered_anomalies = []
        anomaly_keys = set()

        for anomaly in anomalies:
            anomaly_key = AnomalyKey(price=anomaly.price, type=anomaly.type)
            anomaly_keys.add(anomaly_key)

            if self.__handle_first_position_anomaly(
                anomaly, current_time, anomaly_key
            ):
                filtered_anomalies.append(anomaly)
                continue

            if self.__handle_other_position_anomaly(
                anomaly, current_time, anomaly_key
            ):
                filtered_anomalies.append(anomaly)

        self.__remove_anomaly_keys(self._detected_anomalies, anomaly_keys)
        self.__remove_anomaly_keys(self._observing_anomalies, anomaly_keys)

        return filtered_anomalies

    def __handle_first_position_anomaly(
        self,
        anomaly: OrderAnomaly,
        current_time: float,
        anomaly_key: AnomalyKey,
    ) -> bool:
        if anomaly.position != 0:
            return False

        if anomaly_key not in self._detected_anomalies:
            self._detected_anomalies[anomaly_key] = current_time
            self._observing_anomalies.pop(anomaly_key, None)
            return True

        return False

    def __handle_other_position_anomaly(
        self,
        anomaly: OrderAnomaly,
        current_time: float,
        anomaly_key: AnomalyKey,
    ) -> bool:
        detected_anomaly = self._detected_anomalies.get(anomaly_key)
        observing_anomaly = self._observing_anomalies.get(anomaly_key)

        if detected_anomaly and detected_anomaly < (
            current_time - self._anomalies_detection_ttl
        ):
            self._detected_anomalies.pop(anomaly_key, None)

        if not observing_anomaly:
            self._detected_anomalies[anomaly_key] = current_time
            self._observing_anomalies[anomaly_key] = ObservingOrderAnomaly(
                order_anomaly=OrderAnomaly(
                    price=anomaly.price,
                    quantity=anomaly.quantity,
                    order_liquidity=anomaly.order_liquidity,
                    average_liquidity=anomaly.average_liquidity,
                    position=anomaly.position,
                    type=anomaly.type,
                ),
                time=current_time,
            )
            return False

        if observing_anomaly.time < (
            current_time - self._anomalies_observing_ttl
        ):
            deviation = (
                abs(
                    observing_anomaly.order_anomaly.order_liquidity
                    - anomaly.order_liquidity
                )
                / observing_anomaly.order_anomaly.order_liquidity
            )

            if deviation < self._anomalies_observing_ratio:
                self._observing_anomalies.pop(anomaly_key, None)
                return True
            else:
                self._observing_anomalies.pop(anomaly_key, None)
                return False

        return False

    def __remove_anomaly_keys(
        self, anomalies_dict: Dict, anomaly_keys: Set
    ) -> None:
        keys_to_remove = set(anomalies_dict.keys()) - anomaly_keys
        for key in keys_to_remove:
            del anomalies_dict[key]

    def __get_sorted_top_orders(
        self, orders: Dict[Decimal, Decimal], order_type: Literal["ask", "bid"]
    ) -> Dict[Decimal, Decimal]:
        reverse = order_type == "bid"
        return dict(
            sorted(orders.items(), key=lambda item: item[0], reverse=reverse)[
                : self._top_n_orders
            ]
        )
