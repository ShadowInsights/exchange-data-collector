import asyncio
from decimal import Decimal
from typing import List

from app.application.messengers.orders_anomalies_summary_messenger import (
    OrdersAnomaliesSummaryMessenger, OrdersAnomaliesSummaryNotification)
from app.config import settings
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.repositories.pair_repository import \
    get_pair_and_exchange
from app.infrastructure.messengers.common import BaseMessage, Field
from app.infrastructure.messengers.discord_messenger import DiscordMessenger
from app.utilities.string_utils import add_comma_every_n_symbols, to_title_case


class OrdersAnomaliesSummaryDiscordMessenger(
    OrdersAnomaliesSummaryMessenger, DiscordMessenger
):
    def __init__(self) -> None:
        super().__init__()

    async def _send_notification(
        self, message: BaseMessage, embed_color: int | str
    ) -> None:
        await self._send(message=message, embed_color=embed_color)

    async def send_notification(
        self, notification: OrdersAnomaliesSummaryNotification
    ) -> None:
        fields = []

        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=notification.pair_id
            )

        formatted_exchange_name = to_title_case(str(exchange.name))

        description = (
            f"Anomaly liquidity difference was detected between asks and bids "
            f"for **{pair.symbol}** on **{formatted_exchange_name}**"
        )
        if notification.deviation is not None:
            deviation_field = Field(
                name="Deviation",
                value=f"{self._format_anomaly_fields(notification.deviation)}",
                inline=True,
            )

            fields.append(deviation_field)

        liquidity_difference_field = Field(
            name="Liquidity difference",
            value=f"Current: {self._format_anomaly_fields(notification.current_total_difference)}\n "
            f"Previous: {self._format_anomaly_fields(notification.previous_total_difference)}",
            inline=True,
        )

        fields.append(liquidity_difference_field)

        message = self._create_message(
            "Order Anomaly Summary", description, fields
        )
        embed_color = settings.DISCORD_ORDER_ANOMALIES_SUMMARY_EMBED_COLOR

        asyncio.create_task(
            self._send_notification(message=message, embed_color=embed_color)
        )

    def _create_message(
        self, title: str, description: str, fields: List[Field]
    ) -> BaseMessage:
        return BaseMessage(
            title=title,
            description=description,
            fields=fields,
        )

    def _format_anomaly_fields(self, decimal: Decimal) -> str:
        formatted_price = add_comma_every_n_symbols(f"{decimal: .2f}")

        return formatted_price
