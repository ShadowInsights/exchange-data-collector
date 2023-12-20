from decimal import Decimal
from typing import NamedTuple

from app.application.messengers.common import define_trend_status_by_deviation
from app.application.messengers.orders_anomalies_summary_messenger import (
    OrdersAnomaliesSummaryMessenger,
    OrdersAnomaliesSummaryNotification,
)
from app.infrastructure.db.database import get_async_db
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

BASE_EMOJI = "⚠️"


class FormattedNotification(NamedTuple):
    deviation: str | None
    pair: str
    current_total_difference: str
    previous_total_difference: str
    upper_case_exchange_name: str
    title_case_exchange_name: str


class OrdersAnomaliesSummaryTelegramMessenger(
    OrdersAnomaliesSummaryMessenger, TelegramMessenger
):
    def __init__(self) -> None:
        super().__init__()

    async def send_notification(
        self, notification: OrdersAnomaliesSummaryNotification
    ) -> None:
        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=notification.pair_id
            )

        message = self.__prepare_message(
            deviation=notification.deviation,
            current_total_difference=notification.current_total_difference,
            previous_total_difference=notification.previous_total_difference,
            exchange_name=str(exchange.name),
            pair_symbol=pair.symbol,
        )

        await self._send(message=message)

    def __prepare_message(
        self,
        deviation: Decimal | None,
        current_total_difference: Decimal,
        previous_total_difference: Decimal,
        pair_symbol: str,
        exchange_name: str,
    ) -> BaseMessage:
        liquidity_change_vector = define_trend_status_by_deviation(
            deviation=deviation
        )

        formatted_notification = self.__format_anomaly_fields(
            deviation=deviation,
            pair_symbol=pair_symbol,
            exchange_name=exchange_name,
            current_total_difference=current_total_difference,
            previous_total_difference=previous_total_difference,
        )

        deviation_description = ""
        if deviation is not None:
            deviation_description = (
                f"in *{formatted_notification.deviation}* times"
            )

        description = (
            f"{BASE_EMOJI} #{formatted_notification.pair} #SUMMARY #{formatted_notification.upper_case_exchange_name}\n"
            f"Summary liquidity of *{formatted_notification.pair}* anomalies {liquidity_change_vector.value} "
            f"{deviation_description} from {formatted_notification.previous_total_difference} "
            f"to {formatted_notification.current_total_difference} "
            f"on {formatted_notification.title_case_exchange_name}"
        )

        return BaseMessage(description=description, fields=[])

    def __format_anomaly_fields(
        self,
        deviation: Decimal | None,
        pair_symbol: str,
        current_total_difference: Decimal,
        previous_total_difference: Decimal,
        exchange_name: str,
    ) -> FormattedNotification:
        formatted_deviation = add_comma_every_n_symbols(f"{deviation: .2f}")
        formatted_pair = replace_char(pair_symbol, "/", "")
        formatted_current_total_difference = add_comma_every_n_symbols(
            f"{current_total_difference: .2f}"
        )
        formatted_previous_total_difference = add_comma_every_n_symbols(
            f"{previous_total_difference: .2f}"
        )
        formatted_upper_case_exchange_name = to_upper_case(exchange_name)
        formatted_title_case_exchange_name = to_title_case(exchange_name)

        return FormattedNotification(
            deviation=formatted_deviation,
            pair=formatted_pair,
            current_total_difference=formatted_current_total_difference,
            previous_total_difference=formatted_previous_total_difference,
            upper_case_exchange_name=formatted_upper_case_exchange_name,
            title_case_exchange_name=formatted_title_case_exchange_name,
        )
