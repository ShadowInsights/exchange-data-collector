from decimal import Decimal
from typing import Tuple
from uuid import UUID

from app.common.database import get_async_db
from app.db.models.exchange import ExchangeModel
from app.db.models.pair import PairModel
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.pair_repository import find_pair_by_id
from app.services.messengers.common import BaseMessage, Field
from app.services.messengers.telegram.telegram_messenger import (
    TelegramMessenger,
)
from app.services.messengers.volume_messenger import (
    VolumeMessenger,
    VolumeNotification,
)
from app.utils.string_utils import (
    add_comma_every_n_symbols,
    replace_char,
    to_title_case,
)

EMOJI = "📊"
DEPTH_INCREASED = "⬆️"
DEPTH_DECREASED = "⬇️"


class VolumeTelegramMessenger(VolumeMessenger, TelegramMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def send_notification(
        self, notification: VolumeNotification
    ) -> None:
        exchange, pair = await self._get_exchange_and_pair(
            pair_id=notification.pair_id
        )
        formatted_exchange_name = to_title_case(str(exchange.name))

        message = self.__prepare_message(
            deviation=notification.deviation,
            current_average_volume=Decimal(notification.current_avg_volume),
            previous_average_volume=Decimal(notification.previous_avg_volume),
            current_bid_ask_ratio=notification.current_bid_ask_ratio,
            previous_bid_ask_ratio=notification.previous_bid_ask_ratio,
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
        deviation: Decimal,
        current_average_volume: Decimal,
        previous_average_volume: Decimal,
        current_bid_ask_ratio: Decimal,
        previous_bid_ask_ratio: Decimal,
        exchange_name: str,
        pair: PairModel,
    ) -> BaseMessage:
        if deviation < 1:
            depth_change_vector = "decreased"
        else:
            depth_change_vector = "increased"

        depth_vector_emoji = (
            DEPTH_INCREASED
            if depth_change_vector == "increased"
            else DEPTH_DECREASED
        )

        formatted_pair = replace_char(pair.symbol, "/", "")

        [
            formatted_deviation,
            formatted_current_average_volume,
            formatted_previous_liquidity,
            formatted_bid_ask_ratio,
            formatted_previous_bid_ask_ratio,
        ] = self._format_anomaly_fields(
            deviation,
            current_average_volume,
            previous_average_volume,
            current_bid_ask_ratio,
            previous_bid_ask_ratio,
        )

        description = (
            f"{EMOJI}{depth_vector_emoji} #{formatted_pair} "
            f"depth {depth_change_vector} "
            f"to {formatted_current_average_volume} "
            f"with {formatted_deviation} deviation from average - {formatted_previous_liquidity} "
            f"#{exchange_name}"
        )

        fields = [
            Field(
                name="Bid & Ask ratio",
                value=formatted_bid_ask_ratio,
                inline=False,
            ),
            Field(
                name="Previous",
                value=formatted_previous_bid_ask_ratio,
                inline=False,
            ),
        ]

        return BaseMessage(description=description, fields=fields)

    def _format_anomaly_fields(
        self,
        deviation: Decimal,
        current_average_volume: Decimal,
        previous_average_volume: Decimal,
        current_bid_ask_ratio: Decimal,
        previous_bid_ask_ratio: Decimal,
    ) -> Tuple[str | None, str, str, str, str]:
        formatted_deviation = add_comma_every_n_symbols(f"{deviation: .2f}")

        formatted_current_average_volume = add_comma_every_n_symbols(
            f"{current_average_volume: .2f}"
        )
        formatted_previous_average_volume = add_comma_every_n_symbols(
            f"{previous_average_volume: .2f}"
        )
        formatted_current_bid_ask_ratio = add_comma_every_n_symbols(
            f"{current_bid_ask_ratio: .2f}"
        )
        formatted_previous_bid_ask_ratio = add_comma_every_n_symbols(
            f"{previous_bid_ask_ratio: .2f}"
        )

        return (
            formatted_deviation,
            formatted_current_average_volume,
            formatted_previous_average_volume,
            formatted_current_bid_ask_ratio,
            formatted_previous_bid_ask_ratio,
        )
