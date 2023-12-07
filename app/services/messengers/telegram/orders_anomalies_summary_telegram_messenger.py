from decimal import Decimal
from typing import Tuple
from uuid import UUID

from app.common.database import get_async_db
from app.db.models.exchange import ExchangeModel
from app.db.models.pair import PairModel
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.pair_repository import find_pair_by_id
from app.services.messengers.common import BaseMessage, Field
from app.services.messengers.orders_anomalies_summary_messenger import (
    OrdersAnomaliesSummaryMessenger,
    OrdersAnomaliesSummaryNotification,
)
from app.services.messengers.telegram.telegram_messenger import (
    TelegramMessenger,
)
from app.utils.string_utils import (
    add_comma_every_n_symbols,
    replace_char,
    to_title_case,
)

EMOJI = "⚠️"


class OrdersAnomaliesSummaryTelegramMessenger(
    OrdersAnomaliesSummaryMessenger, TelegramMessenger
):
    def __init__(self) -> None:
        super().__init__()

    async def send_notification(
        self, notification: OrdersAnomaliesSummaryNotification
    ) -> None:
        exchange, pair = await self._get_exchange_and_pair(
            pair_id=notification.pair_id
        )
        formatted_exchange_name = to_title_case(str(exchange.name))

        message = self.__prepare_message(
            deviation=notification.deviation,
            current_total_difference=notification.current_total_difference,
            previous_total_difference=notification.previous_total_difference,
            exchange_name=formatted_exchange_name,
            pair=pair,
        )

        await self._send(message=message)

    async def _get_exchange_and_pair(
        self, pair_id: UUID
    ) -> Tuple[ExchangeModel, PairModel]:
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)
        return exchange, pair

    def __prepare_message(
        self,
        deviation: Decimal | None,
        current_total_difference: Decimal,
        previous_total_difference: Decimal,
        pair: PairModel,
        exchange_name: str,
    ) -> BaseMessage:
        formatted_pair = replace_char(pair.symbol, "/", "")

        description = (
            f"{EMOJI} Anomaly liquidity difference was detected between asks and bids #{exchange_name}"
            f" #{formatted_pair}"
        )

        fields = []

        if deviation is not None:
            fields.append(
                Field(
                    name="Deviation",
                    value=self._format_anomaly_fields(deviation),
                    inline=False,
                )
            )

        fields.append(
            Field(
                name="Current liquidity dif",
                value=self._format_anomaly_fields(current_total_difference),
                inline=False,
            )
        )
        fields.append(
            Field(
                name="Previous liquidity dif",
                value=self._format_anomaly_fields(previous_total_difference),
                inline=False,
            )
        )

        return BaseMessage(description=description, fields=fields)

    def _format_anomaly_fields(self, decimal: Decimal) -> str:
        formatted_decimal = add_comma_every_n_symbols(f"{decimal: .2f}")

        return formatted_decimal
