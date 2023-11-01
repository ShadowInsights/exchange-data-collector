import asyncio
import concurrent.futures
import copy
import logging
from decimal import Decimal
from typing import Dict, List, Literal, NamedTuple, Set

from app.common.config import settings
from app.common.database import get_async_db
from app.db.models.order_book_anomaly import OrderBookAnomalyModel
from app.db.repositories.order_book_anomaly_repository import \
    create_order_book_anomalies
from app.services.clients.schemas.binance import OrderBookSnapshot
from app.services.collectors.common import Collector, OrderBook
from app.services.collectors.workers.common import Worker
from app.services.messengers.order_book_discord_messenger import (
    OrderAnomalyNotification, OrderBookDiscordMessenger)
from app.utils.math_utils import calculate_average_excluding_value_from_sum
from app.utils.scheduling_utils import set_interval
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


class OrderAnomalyDto(NamedTuple):
    time: float
    order_anomaly: OrderAnomaly


class PositionedOrder(NamedTuple):
    position: int
    price: Decimal
    quantity: Decimal
    liquidity: Decimal


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
        anomalies_significantly_increased_ratio: float = settings.ANOMALIES_SIGNIFICANTLY_INCREASED_RATIO,
        executor_factory: concurrent.futures.Executor = None,
        order_anomaly_minimum_liquidity: float = settings.ORDER_ANOMALY_MINIMUM_LIQUIDITY,
        maximum_order_book_anomalies: int = settings.MAXIMUM_ORDER_BOOK_ANOMALIES,
    ):
        self._collector = collector
        self._discord_messenger = discord_messenger
        self._detected_anomalies: Dict[AnomalyKey, OrderAnomalyDto] = {}
        self._observing_anomalies: Dict[AnomalyKey, OrderAnomalyDto] = {}
        self._orders_anomaly_multiplier = Decimal(order_anomaly_multiplier)
        self._anomalies_detection_ttl = anomalies_detection_ttl
        self._anomalies_observing_ttl = anomalies_observing_ttl
        self._anomalies_observing_ratio = Decimal(anomalies_observing_ratio)
        self._top_n_orders = top_n_orders
        self._anomalies_significantly_increased_ratio = (
            anomalies_significantly_increased_ratio
        )
        # TODO: add support for different executor types
        self._executor_factory = (
            executor_factory or concurrent.futures.ThreadPoolExecutor
        )
        self._order_anomaly_minimum_liquidity = Decimal(
            order_anomaly_minimum_liquidity
        )
        self._maximum_order_book_anomalies = maximum_order_book_anomalies + 1

    @set_interval(settings.ORDERS_WORKER_JOB_INTERVAL)
    async def run(self) -> None:
        await super().run()

    async def _run_worker(self) -> None:
        await self.__process_orders()

    async def __process_orders(self) -> None:
        logging.debug(
            f"Orders processing cycle started [symbol={self._collector.symbol}]"
        )

        filtered_anomalies = await self.__get_filtered_anomalies()

        if filtered_anomalies:
            save_anomalies = self.__save_anomalies(filtered_anomalies)
            send_anomalies = self.__send_anomalies(filtered_anomalies)
            await asyncio.gather(save_anomalies, send_anomalies)

    async def __get_filtered_anomalies(self):
        order_book = copy.deepcopy(self._collector.order_book)
        delimiter = copy.deepcopy(self._collector.delimiter)

        with self._executor_factory() as executor:
            result = await asyncio.get_event_loop().run_in_executor(
                executor,
                self.__calculate_filtered_anomalies,
                order_book,
                delimiter,
            )

        return result

    async def __save_anomalies(self, anomalies: List[OrderAnomaly]) -> None:
        order_book_anomalies = [
            OrderBookAnomalyModel(
                launch_id=self._collector.launch_id,
                pair_id=self._collector.pair_id,
                price=anomaly.price,
                quantity=anomaly.quantity,
                order_liquidity=anomaly.order_liquidity,
                average_liquidity=anomaly.average_liquidity,
                position=anomaly.position,
                type=anomaly.type,
            )
            for anomaly in anomalies
        ]
        async with get_async_db() as session:
            await create_order_book_anomalies(session, order_book_anomalies)

    async def __send_anomalies(self, anomalies: List[OrderAnomaly]) -> None:
        order_anomaly_notifications = [
            OrderAnomalyNotification(
                price=anomaly.price,
                quantity=anomaly.quantity,
                order_liquidity=anomaly.order_liquidity,
                average_liquidity=anomaly.average_liquidity,
                type=anomaly.type,
                position=anomaly.position,
            )
            for anomaly in anomalies
        ]
        await self._discord_messenger.send_notifications(
            order_anomaly_notifications,
            self._collector.pair_id,
        )

    def __calculate_filtered_anomalies(
        self, order_book: OrderBookSnapshot, delimiter: Decimal
    ):
        current_order_book = self.__group_orders(order_book, delimiter)
        anomalies = self.__find_anomalies(current_order_book)
        filtered_anomalies = self.__filter_anomalies(anomalies)
        return filtered_anomalies

    def __group_orders(
        self, order_book: OrderBookSnapshot, delimiter: Decimal
    ) -> OrderBook:
        return OrderBook(
            a=self.group_order_book(order_book.asks, delimiter),
            b=self.group_order_book(order_book.bids, delimiter),
        )

    def __find_anomalies(self, order_book: OrderBook) -> List[OrderAnomaly]:
        return self.__get_anomalies(
            order_book.a, "ask"
        ) + self.__get_anomalies(order_book.b, "bid")

    def __get_anomalies(
        self, orders: Dict[Decimal, Decimal], order_type: Literal["ask", "bid"]
    ) -> list[OrderAnomaly]:
        top_orders = self.__get_sorted_top_orders(orders, order_type)

        if len(top_orders) <= 1:
            return []

        order_book_liquidity = 0
        positioned_orders: list[PositionedOrder] = []

        for position, (price, qty) in enumerate(top_orders.items()):
            order_liquidity = price * qty
            order_book_liquidity += order_liquidity
            positioned_orders.append(
                PositionedOrder(
                    position=position,
                    price=price,
                    quantity=qty,
                    liquidity=order_liquidity,
                )
            )

        sorted_positioned_orders = sorted(
            positioned_orders, key=lambda order: order.liquidity, reverse=True
        )

        anomalies: list[OrderAnomaly] = []

        for i in range(1, len(sorted_positioned_orders)):
            if i == self._maximum_order_book_anomalies:
                anomalies = []
                break

            current_order = sorted_positioned_orders[i]
            previous_order = sorted_positioned_orders[i - 1]

            current_available_liquidity = (
                calculate_average_excluding_value_from_sum(
                    order_book_liquidity,
                    len(sorted_positioned_orders) - 1,
                    previous_order.liquidity,
                )
            )

            if previous_order.liquidity < current_available_liquidity / len(
                sorted_positioned_orders
            ):
                break

            if (
                previous_order.liquidity
                > self._orders_anomaly_multiplier * current_order.liquidity
            ):
                if (
                    current_order.liquidity
                    < self._order_anomaly_minimum_liquidity
                ):
                    break
                else:
                    for order in sorted_positioned_orders[:i]:
                        average_liquidity = (
                            calculate_average_excluding_value_from_sum(
                                order_book_liquidity,
                                len(sorted_positioned_orders) - 1,
                                previous_order.liquidity,
                            )
                        )
                        anomalies.append(
                            OrderAnomaly(
                                price=order.price,
                                quantity=order.quantity,
                                order_liquidity=order.liquidity,
                                average_liquidity=average_liquidity,
                                position=order.position,
                                type=order_type,
                            )
                        )
                    break

        return anomalies

    def __filter_anomalies(
        self, anomalies: List[OrderAnomaly]
    ) -> List[OrderAnomaly]:
        current_time = get_current_time()
        filtered_anomalies = []
        anomaly_keys = set()

        # Remove expired anomalies keys in cache
        self.__remove_expired_anomaly_keys(
            anomalies_dict=self._detected_anomalies, current_time=current_time
        )

        for anomaly in anomalies:
            anomaly_key = AnomalyKey(price=anomaly.price, type=anomaly.type)
            anomaly_keys.add(anomaly_key)

            # Additional filter logic only for first position anomalies
            if self.__handle_first_position_anomaly(
                anomaly, anomaly_key, current_time
            ):
                filtered_anomalies.append(anomaly)
                continue

            # Additional filter logic only for non-first position anomalies
            if self.__handle_other_position_anomaly(
                anomaly, current_time, anomaly_key
            ):
                filtered_anomalies.append(anomaly)

        # Delete keys of previous anomalies that were sent to observing but now are missed
        self.__remove_anomaly_keys(self._observing_anomalies, anomaly_keys)

        return filtered_anomalies

    # Common input filter logic for anomalies in any position
    def __handle_any_position_anomaly(
        self,
        anomaly: OrderAnomaly,
        anomaly_key: AnomalyKey,
    ) -> bool:
        # Pass anomaly if it's not cached
        if anomaly_key not in self._detected_anomalies:
            return True

        # Pass anomaly if it's cached, but it's volume significantly increased
        if self.__is_volume_significantly_increased(
            anomaly=anomaly, anomaly_key=anomaly_key
        ):
            return True

        return False

    def __handle_first_position_anomaly(
        self,
        anomaly: OrderAnomaly,
        anomaly_key: AnomalyKey,
        current_time: float,
    ) -> bool:
        if anomaly.position != 0:
            return False

        if self.__handle_any_position_anomaly(
            anomaly=anomaly, anomaly_key=anomaly_key
        ):
            self._detected_anomalies[anomaly_key] = OrderAnomalyDto(
                time=current_time, order_anomaly=anomaly
            )
            self._observing_anomalies.pop(anomaly_key, None)
            return True

        return False

    def __handle_other_position_anomaly(
        self,
        anomaly: OrderAnomaly,
        current_time: float,
        anomaly_key: AnomalyKey,
    ) -> bool:
        observing_anomaly = self._observing_anomalies.get(anomaly_key)

        # Check if we placed this anomaly before for observing and its time for making conclusion has come
        if observing_anomaly and observing_anomaly.time < (
            current_time - self._anomalies_observing_ttl
        ):
            # Calculating volume change during observing time
            deviation = (
                abs(
                    observing_anomaly.order_anomaly.order_liquidity
                    - anomaly.order_liquidity
                )
                / observing_anomaly.order_anomaly.order_liquidity
            )

            # It's anomaly, if deviation of volume is less than ratio in settings
            if deviation < self._anomalies_observing_ratio:
                self._observing_anomalies.pop(anomaly_key, None)
                return True
            else:
                self._observing_anomalies.pop(anomaly_key, None)
                return False

        # if conditions are met, place for observing and in cache
        if self.__handle_any_position_anomaly(
            anomaly=anomaly, anomaly_key=anomaly_key
        ):
            order_anomaly: OrderAnomalyDto = OrderAnomalyDto(
                order_anomaly=anomaly, time=current_time
            )

            self._detected_anomalies[anomaly_key] = order_anomaly
            self._observing_anomalies[anomaly_key] = order_anomaly

            return False

        return False

    def __remove_anomaly_keys(
        self, anomalies_dict: Dict, anomaly_keys: Set
    ) -> None:
        keys_to_remove = set(anomalies_dict.keys()) - anomaly_keys
        for key in keys_to_remove:
            del anomalies_dict[key]

    def __remove_expired_anomaly_keys(
        self,
        anomalies_dict: Dict[AnomalyKey, OrderAnomalyDto],
        current_time: float,
    ) -> None:
        keys_to_remove = [
            key
            for key, value in anomalies_dict.items()
            if value.time < current_time - self._anomalies_detection_ttl
        ]

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

    def __is_volume_significantly_increased(
        self, anomaly: OrderAnomaly, anomaly_key: AnomalyKey
    ) -> bool:
        cached_volume = self._detected_anomalies[
            anomaly_key
        ].order_anomaly.order_liquidity
        return (
            anomaly.order_liquidity / cached_volume
            >= self._anomalies_significantly_increased_ratio
        )
