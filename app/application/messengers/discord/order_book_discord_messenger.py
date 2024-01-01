from asyncio import gather
from typing import List, NamedTuple
from uuid import UUID

from app.application.messengers.order_book_messenger import (
    OrderAnomalyNotification, OrderBookMessenger)
from app.config import settings
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.repositories.pair_repository import \
    get_pair_and_exchange
from app.infrastructure.messengers.common import BaseMessage, Field
from app.infrastructure.messengers.discord_messenger import DiscordMessenger
from app.utilities.string_utils import (add_comma_every_n_symbols,
                                        round_decimal_to_first_non_zero,
                                        to_title_case)


class FormattedNotification(NamedTuple):
    price: str
    quantity: str
    liquidity: str
    order_liquidity: str


class OrderBookDiscordMessenger(OrderBookMessenger, DiscordMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def _send_notification(
        self, message: BaseMessage, embed_color: int | str
    ) -> None:
        await self._send(message=message, embed_color=embed_color)

    async def send_anomaly_detection_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=pair_id
            )

        formatted_exchange_name = to_title_case(str(exchange.name))

        notification_tasks = []
        for anomaly in anomalies:
            formatted_notification = self._format_anomaly_fields(anomaly)
            description = (
                f"Order anomaly {anomaly.type} was detected "
                f"for **{pair.symbol}** on **{formatted_exchange_name}**"
            )
            fields = [
                Field(
                    name="Order",
                    value=f"Price: {formatted_notification.price}\nQuantity: {formatted_notification.quantity}",
                    inline=True,
                ),
                Field(
                    name="Average liquidity",
                    value=formatted_notification.liquidity,
                    inline=True,
                ),
                Field(
                    name="Order liquidity",
                    value=formatted_notification.order_liquidity,
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
        destiny_color: int | str,
    ) -> None:
        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=pair_id
            )

        formatted_exchange_name = to_title_case(str(exchange.name))

        cancellation_tasks = []
        for anomaly in anomalies:
            formatted_notification = self._format_anomaly_fields(anomaly)
            description = (
                f"Order anomaly {anomaly.type} was {destiny} "
                f"for **{pair.symbol}** on **{formatted_exchange_name}**"
            )
            fields = [
                Field(
                    name="Order",
                    value=f"Price: {formatted_notification.price}\nQuantity: {formatted_notification.quantity}",
                    inline=True,
                ),
                Field(
                    name="Average liquidity",
                    value=formatted_notification.liquidity,
                    inline=True,
                ),
                Field(
                    name="Order liquidity",
                    value=formatted_notification.order_liquidity,
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

    def _create_message(
        self, title: str, description: str, fields: List[Field]
    ) -> BaseMessage:
        return BaseMessage(
            title=title,
            description=description,
            fields=fields,
        )

    def _format_anomaly_fields(
        self, anomaly: OrderAnomalyNotification
    ) -> FormattedNotification:
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

        return FormattedNotification(
            formatted_price,
            formatted_quantity,
            formatted_liquidity,
            formatted_order_liquidity,
        )
