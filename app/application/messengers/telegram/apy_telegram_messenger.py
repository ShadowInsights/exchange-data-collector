from decimal import Decimal
from typing import NamedTuple

from app.application.messengers.apy_messenger import (APYMessenger,
                                                      APYNotification)
from app.application.messengers.common import (
    TrendStatus, define_trend_status_by_deviation)
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.models.apy_asset import APYAsset
from app.infrastructure.db.repositories.apy_asset_repository import \
    get_apy_asset_and_exchange
from app.infrastructure.messengers.common import BaseMessage
from app.infrastructure.messengers.telegram_messenger import TelegramMessenger
from app.utilities.string_utils import (add_comma_every_n_symbols,
                                        replace_char, to_title_case,
                                        to_upper_case)

BASE_EMOJI = "📊"
UP_TREND_EMOJI = "⬆️"
DOWN_TREND_EMOJI = "⬇️"


class FormattedNotification(NamedTuple):
    deviation: str
    pair: str
    current_apy: str
    previous_apy: str
    upper_case_exchange_name: str
    title_case_exchange_name: str


class APYTelegramMessenger(APYMessenger, TelegramMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def send_notification(self, notification: APYNotification) -> None:
        async with get_async_db() as session:
            apy_asset, exchange = await get_apy_asset_and_exchange(
                session=session, apy_asset_id=notification.apy_asset_id
            )

        message = self.__prepare_message(
            deviation=notification.deviation,
            current_apy=Decimal(notification.current_apy),
            previous_apy=Decimal(notification.previous_apy),
            exchange_name=str(exchange.name),
            apy_asset=apy_asset,
        )

        await self._send(message=message)

    def __prepare_message(
        self,
        deviation: Decimal,
        current_apy: Decimal,
        previous_apy: Decimal,
        exchange_name: str,
        apy_asset: APYAsset,
    ) -> BaseMessage:
        apy_change_vector = define_trend_status_by_deviation(
            deviation=deviation
        )
        depth_vector_emoji = self.__choose_appropriate_emoji(apy_change_vector)

        formatted_notification = self.__format_anomaly_fields(
            deviation,
            apy_asset.symbol,
            current_apy,
            previous_apy,
            exchange_name,
        )

        description = (
            f"{BASE_EMOJI}{depth_vector_emoji} "
            f"#{formatted_notification.pair} #APY "
            f"#{formatted_notification.upper_case_exchange_name}\n"
            f"*{formatted_notification.pair}* apy "
            f"{apy_change_vector.value} in *{formatted_notification.deviation}* times "
            f"from {formatted_notification.previous_apy} to {formatted_notification.current_apy} "
            f"on {formatted_notification.title_case_exchange_name}"
        )

        return BaseMessage(description=description, fields=[])

    def __format_anomaly_fields(
        self,
        deviation: Decimal,
        apy_asset_symbol: str,
        current_average_volume: Decimal,
        previous_average_volume: Decimal,
        exchange_name: str,
    ) -> FormattedNotification:
        formatted_deviation = add_comma_every_n_symbols(f"{deviation: .2f}")
        formatted_apy_asset = replace_char(apy_asset_symbol, "/", "")
        formatted_current_apy = add_comma_every_n_symbols(
            f"{current_average_volume: .2f}"
        )
        formatted_previous_apy = add_comma_every_n_symbols(
            f"{previous_average_volume: .2f}"
        )
        formatted_upper_case_exchange_name = to_upper_case(exchange_name)
        formatted_title_case_exchange_name = to_title_case(exchange_name)

        return FormattedNotification(
            formatted_deviation,
            formatted_apy_asset,
            formatted_current_apy,
            formatted_previous_apy,
            formatted_upper_case_exchange_name,
            formatted_title_case_exchange_name,
        )

    def __choose_appropriate_emoji(
        self, apy_change_vector: TrendStatus
    ) -> str:
        return (
            UP_TREND_EMOJI
            if apy_change_vector.name == TrendStatus.INCREASED
            else DOWN_TREND_EMOJI
        )
