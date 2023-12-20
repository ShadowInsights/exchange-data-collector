from decimal import Decimal
from typing import NamedTuple

from app.application.messengers.common import (
    TrendStatus,
    define_trend_status_by_deviation,
)
from app.application.messengers.volume_messenger import (
    VolumeMessenger,
    VolumeNotification,
)
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.models.pair import PairModel
from app.infrastructure.db.repositories.pair_repository import (
    get_pair_and_exchange,
)
from app.infrastructure.messengers.common import BaseMessage
from app.infrastructure.messengers.telegram_messenger import TelegramMessenger
from app.utilities.string_utils import (
    add_comma_every_n_symbols,
    replace_char,
    to_title_case,
    to_upper_case,
)

BASE_EMOJI = "📊"
UP_TREND_EMOJI = "⬆️"
DOWN_TREND_EMOJI = "⬇️"


class FormattedNotification(NamedTuple):
    deviation: str
    pair: str
    current_average_volume: str
    previous_average_volume: str
    upper_case_exchange_name: str
    title_case_exchange_name: str


class VolumeTelegramMessenger(VolumeMessenger, TelegramMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def send_notification(
        self, notification: VolumeNotification
    ) -> None:
        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=notification.pair_id
            )

        message = self.__prepare_message(
            deviation=notification.deviation,
            current_average_volume=Decimal(notification.current_avg_volume),
            previous_average_volume=Decimal(notification.previous_avg_volume),
            exchange_name=str(exchange.name),
            pair=pair,
        )

        await self._send(message=message)

    def __prepare_message(
        self,
        deviation: Decimal,
        current_average_volume: Decimal,
        previous_average_volume: Decimal,
        exchange_name: str,
        pair: PairModel,
    ) -> BaseMessage:
        depth_change_vector = define_trend_status_by_deviation(
            deviation=deviation
        )
        depth_vector_emoji = self.__choose_appropriate_emoji(
            depth_change_vector
        )

        formatted_notification = self.__format_anomaly_fields(
            deviation,
            pair.symbol,
            current_average_volume,
            previous_average_volume,
            exchange_name,
        )

        description = (
            f"{BASE_EMOJI}{depth_vector_emoji} "
            f"#{formatted_notification.pair} #DEPTH "
            f"#{formatted_notification.upper_case_exchange_name}\n"
            f"*{formatted_notification.pair}* depth "
            f"{depth_change_vector.value} in *{formatted_notification.deviation}* times "
            f"from {formatted_notification.previous_average_volume} to {formatted_notification.current_average_volume} "
            f"on {formatted_notification.title_case_exchange_name}"
        )

        return BaseMessage(description=description, fields=[])

    def __format_anomaly_fields(
        self,
        deviation: Decimal,
        pair_symbol: str,
        current_average_volume: Decimal,
        previous_average_volume: Decimal,
        exchange_name: str,
    ) -> FormattedNotification:
        formatted_deviation = add_comma_every_n_symbols(f"{deviation: .2f}")
        formatted_pair = replace_char(pair_symbol, "/", "")
        formatted_current_average_volume = add_comma_every_n_symbols(
            f"{current_average_volume: .2f}"
        )
        formatted_previous_average_volume = add_comma_every_n_symbols(
            f"{previous_average_volume: .2f}"
        )
        formatted_upper_case_exchange_name = to_upper_case(exchange_name)
        formatted_title_case_exchange_name = to_title_case(exchange_name)

        return FormattedNotification(
            formatted_deviation,
            formatted_pair,
            formatted_current_average_volume,
            formatted_previous_average_volume,
            formatted_upper_case_exchange_name,
            formatted_title_case_exchange_name,
        )

    def __choose_appropriate_emoji(
        self, depth_change_vector: TrendStatus
    ) -> str:
        return (
            UP_TREND_EMOJI
            if depth_change_vector.name == TrendStatus.INCREASED
            else DOWN_TREND_EMOJI
        )
