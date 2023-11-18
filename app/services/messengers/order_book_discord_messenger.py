from asyncio import gather
from decimal import Decimal
from typing import List, Literal, NamedTuple, Tuple
from uuid import UUID

from app.common.config import settings
from app.common.database import get_async_db
from app.db.models.exchange import ExchangeModel
from app.db.models.pair import PairModel
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.pair_repository import find_pair_by_id
from app.services.messengers.common import BaseMessage, Field
from app.services.messengers.discord_messenger import DiscordMessenger
from app.utils.string_utils import (add_comma_every_n_symbols,
                                    round_decimal_to_first_non_zero,
                                    to_title_case)


class OrderAnomalyNotification(NamedTuple):
    price: Decimal
    quantity: Decimal
    order_liquidity: Decimal
    average_liquidity: Decimal
    type: Literal["ask", "bid"]
    position: int


class OrderBookDiscordMessenger(DiscordMessenger):
    def __init__(self):
        super().__init__()

    async def _get_exchange_and_pair(
        self, pair_id: UUID
    ) -> Tuple[ExchangeModel, PairModel]:
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)
        return exchange, pair

    def _format_anomaly_fields(
        self, anomaly: OrderAnomalyNotification
    ) -> Tuple[str, str, str, str]:
        formatted_price = add_comma_every_n_symbols(
            round_decimal_to_first_non_zero(anomaly.price)
        )
        formatted_quantity = add_comma_every_n_symbols(
            f"{anomaly.quantity: .2f}"
        )
        formatted_liquidity = add_comma_every_n_symbols(
            f"{anomaly.average_liquidity: .2f}"
        )
        formatted_order_liquidity = add_comma_every_n_symbols(
            f"{anomaly.order_liquidity: .2f}"
        )

        return (
            formatted_price,
            formatted_quantity,
            formatted_liquidity,
            formatted_order_liquidity,
        )

    def _create_message(
        self, title: str, description: str, fields: List[Field]
    ) -> BaseMessage:
        return BaseMessage(
            title=title,
            description=description,
            fields=fields,
        )

    async def _send_notification(
        self, message: BaseMessage, embed_color: int
    ) -> None:
        await self._send(message=message, embed_color=embed_color)

    async def send_anomaly_detection_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        exchange, pair = await self._get_exchange_and_pair(pair_id)
        formatted_exchange_name = to_title_case(exchange.name)

        notification_tasks = []
        for anomaly in anomalies:
            (
                formatted_price,
                formatted_quantity,
                formatted_liquidity,
                formatted_order_liquidity,
            ) = self._format_anomaly_fields(anomaly)
            description = (
                f"Order anomaly {anomaly.type} was detected "
                f"for **{pair.symbol}** on **{formatted_exchange_name}**"
            )
            fields = [
                Field(
                    name="Order",
                    value=f"Price: {formatted_price}\nQuantity: {formatted_quantity}",
                    inline=True,
                ),
                Field(
                    name="Average liquidity",
                    value=formatted_liquidity,
                    inline=True,
                ),
                Field(
                    name="Order liquidity",
                    value=formatted_order_liquidity,
                    inline=True,
                ),
                Field(
                    name="Order position",
                    value="Market" if anomaly.position == 0 else "Limit",
                    inline=False,
                ),
            ]
            message = self._create_message(
                "Order Anomaly", description, fields
            )
            embed_color = (
                settings.DISCORD_ORDER_ANOMALY_ASK_EMBED_COLOR
                if anomaly.type == "ask"
                else settings.DISCORD_ORDER_ANOMALY_BID_EMBED_COLOR
            )
            notification_tasks.append(
                self._send_notification(message, embed_color)
            )

        await gather(*notification_tasks)

    async def send_anomaly_cancellation_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        await self.__send_anomaly_destiny_notifications(
            anomalies,
            pair_id,
            "cancelled",
            settings.DISCORD_ORDER_BOOK_ANOMALY_CANCELED_EMBED_COLOR,
        )

    async def send_anomaly_realization_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        await self.__send_anomaly_destiny_notifications(
            anomalies,
            pair_id,
            "realized",
            settings.DISCORD_ORDER_BOOK_ANOMALY_REALIZED_EMBED_COLOR,
        )

    async def __send_anomaly_destiny_notifications(
        self,
        anomalies: List[OrderAnomalyNotification],
        pair_id: UUID,
        destiny: str,
        destiny_color: str,
    ) -> None:
        exchange, pair = await self._get_exchange_and_pair(pair_id)
        formatted_exchange_name = to_title_case(exchange.name)

        cancellation_tasks = []
        for anomaly in anomalies:
            (
                formatted_price,
                formatted_quantity,
                formatted_liquidity,
                formatted_order_liquidity,
            ) = self._format_anomaly_fields(anomaly)
            description = (
                f"Order anomaly {anomaly.type} was {destiny} "
                f"for **{pair.symbol}** on **{formatted_exchange_name}**"
            )
            fields = [
                Field(
                    name="Order",
                    value=f"Price: {formatted_price}\nQuantity: {formatted_quantity}",
                    inline=True,
                ),
                Field(
                    name="Average liquidity",
                    value=formatted_liquidity,
                    inline=True,
                ),
                Field(
                    name="Order liquidity",
                    value=formatted_order_liquidity,
                    inline=True,
                ),
                Field(
                    name="Order position",
                    value="Market" if anomaly.position == 0 else "Limit",
                    inline=False,
                ),
            ]
            message = self._create_message(
                "Order Anomaly Cancelled", description, fields
            )
            cancellation_tasks.append(
                self._send_notification(
                    message,
                    destiny_color,
                )
            )

        await gather(*cancellation_tasks)
