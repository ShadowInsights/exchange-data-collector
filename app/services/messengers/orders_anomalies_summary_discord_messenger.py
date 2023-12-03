import asyncio
from decimal import Decimal
from typing import Tuple, List
from uuid import UUID

from app.common.config import settings
from app.common.database import get_async_db
from app.db.models.exchange import ExchangeModel
from app.db.models.pair import PairModel
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.pair_repository import find_pair_by_id
from app.services.messengers.common import Field, BaseMessage
from app.services.messengers.discord_messenger import DiscordMessenger
from app.utils.string_utils import (
    to_title_case,
    add_comma_every_n_symbols,
)


class OrdersAnomaliesSummaryDiscordMessenger(DiscordMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def _send_notification(
        self, message: BaseMessage, embed_color: int | str
    ) -> None:
        await self._send(message=message, embed_color=embed_color)

    async def send_notification(
        self,
        pair_id: UUID,
        deviation: Decimal | None,
        current_total_difference: Decimal,
        previous_total_difference: Decimal,
    ) -> None:
        fields = []

        exchange, pair = await self._get_exchange_and_pair(pair_id)
        formatted_exchange_name = to_title_case(str(exchange.name))

        description = (
            f"Anomaly liquidity difference was detected between asks and bids "
            f"for **{pair.symbol}** on **{formatted_exchange_name}**"
        )
        if deviation is not None:
            deviation_field = Field(
                name="Deviation",
                value=f"{self._format_anomaly_fields(deviation)}",
                inline=True,
            )

            fields.append(deviation_field)

        liquidity_difference_field = Field(
            name="Liquidity difference",
            value=f"Current: {self._format_anomaly_fields(current_total_difference)}\n "
            f"Previous: {self._format_anomaly_fields(previous_total_difference)}",
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

    async def _get_exchange_and_pair(
        self, pair_id: UUID
    ) -> Tuple[ExchangeModel, PairModel]:
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)
        return exchange, pair

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
