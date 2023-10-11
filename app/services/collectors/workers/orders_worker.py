import asyncio
import copy
import logging
from decimal import Decimal
from typing import Dict, List, Literal, NamedTuple, Tuple

from app.common.config import settings
from app.common.database import get_async_db
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.pair_repository import find_pair_by_id
from app.services.clients.schemas.binance import OrderBookSnapshot
from app.services.collectors.common import Collector, OrderBook
from app.services.collectors.workers.common import Worker, set_interval
from app.services.messengers.common import BaseMessage, Field
from app.utils.time_utils import get_current_time


class OrderAnomaly(NamedTuple):
    price: Decimal
    quantity: Decimal
    average_liquidity: Decimal
    type: Literal["ask", "bid"] = None


class OrdersWorker(Worker):
    def __init__(self, collector: Collector):
        self._collector = collector
        self._previous_order_book: OrderBook = None
        self._detected_anomalies: Dict[Decimal, float] = {}

    @set_interval(settings.ORDERS_WORKER_JOB_INTERVAL)
    async def run(self) -> None:
        await super().run()

    async def _run_worker(self) -> None:
        await self.__process_orders()

    async def __process_orders(self) -> None:
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
        anomalies = self.__check_anomalies(current_order_book)
        self.__prune_anomalies()

        self._previous_order_book = current_order_book

        if anomalies:
            await self.__send_notification(anomalies)

    def __group_orders(self, order_book: OrderBookSnapshot) -> OrderBook:
        return OrderBook(
            a=self.group_order_book(
                order_book.asks, self._collector.delimiter
            ),
            b=self.group_order_book(
                order_book.bids, self._collector.delimiter
            ),
        )

    def __check_anomalies(self, order_book: OrderBook) -> List[OrderAnomaly]:
        anomaly_asks, average_liquidity = self.__get_anomalies(
            order_book.a, "asks"
        )
        anomaly_bids, average_liquidity = self.__get_anomalies(
            order_book.b, "bids"
        )

        new_anomaly_asks = {
            OrderAnomaly(
                price=price,
                quantity=quantity,
                average_liquidity=average_liquidity,
                type="ask",
            )
            for price, quantity in anomaly_asks.items()
            if price not in self._detected_anomalies
        }
        new_anomaly_bids = {
            OrderAnomaly(
                price=price,
                quantity=quantity,
                average_liquidity=average_liquidity,
                type="bid",
            )
            for price, quantity in anomaly_bids.items()
            if price not in self._detected_anomalies
        }

        current_time = get_current_time()
        for anomaly in new_anomaly_asks:
            self._detected_anomalies[anomaly.price] = current_time
            logging.info(
                f"New anomaly detected in asks [symbol={self._collector.symbol}, "
                f"price={anomaly.price}, quantity={anomaly_asks[anomaly.price]}]"
            )
        for anomaly in new_anomaly_bids:
            self._detected_anomalies[anomaly.price] = current_time
            logging.info(
                f"New anomaly detected in bids [symbol={self._collector.symbol}, "
                f"price={anomaly.price}, quantity={anomaly_bids[anomaly.price]}]"
            )

        return list(new_anomaly_asks) + list(new_anomaly_bids)

    def __get_anomalies(
        self,
        orders: Dict[Decimal, Decimal],
        order_type: Literal["asks", "bids"],
    ) -> Tuple[Dict[Decimal, Decimal], float]:
        top_orders = self.__get_top_orders(orders, order_type)

        if not top_orders:
            return {}

        total_liquidity = sum(price * qty for price, qty in top_orders.items())
        average_liquidity = total_liquidity / len(top_orders)

        anomalies = {
            price: qty
            for price, qty in top_orders.items()
            if price * qty
            > Decimal(settings.ORDER_ANOMALY_MULTIPLIER) * average_liquidity
        }

        return anomalies, average_liquidity

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
            logging.info(
                f"Anomaly expired [symbol={self._collector.symbol}, price={price}]"
            )

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

    async def __send_notification(self, anomalies: List[OrderAnomaly]) -> None:
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=self._collector.pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)

        # Formatting message
        title = "Order Anomaly"
        for anomaly in anomalies:
            formatted_price = "{:.2f}".format(anomaly.price)
            formatted_quantity = "{:.2f}".format(anomaly.quantity)
            formatted_composition = "{:.2f}".format(
                anomaly.price * anomaly.quantity
            )
            description = f"Order anomaly {anomaly.type} was detected for {pair.symbol} on {exchange.name}"
            order_field = Field(
                name="Order",
                value=f"Price: {formatted_price}\nQuantity: "
                f"{formatted_quantity}\nLiquidity: {formatted_composition}",
            )
            total_liquidity_field = Field(
                name="Average liquidity",
                value="{:.2f}".format(anomaly.average_liquidity),
            )
            # Construct message to send
            body = BaseMessage(
                title=title,
                description=description,
                fields=[order_field, total_liquidity_field],
            )
            # Sending message
            asyncio.create_task(self._collector.messenger.send(body))
