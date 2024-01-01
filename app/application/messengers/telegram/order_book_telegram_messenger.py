import asyncio
from enum import Enum
from typing import List, NamedTuple
from uuid import UUID

from app.application.messengers.discord.order_book_discord_messenger import \
    OrderAnomalyNotification
from app.application.messengers.order_book_messenger import OrderBookMessenger
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.models.pair import PairModel
from app.infrastructure.db.repositories.pair_repository import \
    get_pair_and_exchange
from app.infrastructure.messengers.common import BaseMessage, Field
from app.infrastructure.messengers.telegram_messenger import TelegramMessenger
from app.utilities.string_utils import (add_comma_every_n_symbols,
                                        replace_char,
                                        round_decimal_to_first_non_zero,
                                        to_title_case, to_upper_case)

BID_EMOJI = "📈"
ASK_EMOJI = "📉"
CANCELLATION_EMOJI = "✖"
REALIZATION_EMOJI = "✔️"


class AnomalyState(Enum):
    DETECTED = "detected"
    CANCELLED = "cancelled"
    REALIZED = "realized"


class FormattedMessage(NamedTuple):
    quantity: str
    liquidity: str
    order_liquidity: str
    price: str
    upper_case_exchange_name: str
    title_case_exchange_name: str
    pair_symbol: str


class OrderBookTelegramMessenger(OrderBookMessenger, TelegramMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def __send_anomaly_detection(
        self,
        anomalies: List[OrderAnomalyNotification],
        emoji: str,
        destiny: AnomalyState,
        pair_id: UUID,
    ) -> None:
        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=pair_id
            )

        async with asyncio.TaskGroup() as tg:
            for anomaly in anomalies:
                message = self.__prepare_message(
                    anomaly=anomaly,
                    destiny=destiny,
                    emoji=emoji,
                    exchange_name=str(exchange.name),
                    pair=pair,
                )

                tg.create_task(self._send(message=message))

    async def send_anomaly_detection_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=pair_id
            )

        async with asyncio.TaskGroup() as tg:
            for anomaly in anomalies:
                emoji = self.__choose_appropriate_emoji(anomaly.type)

                message = self.__prepare_message(
                    anomaly=anomaly,
                    destiny=AnomalyState.DETECTED,
                    emoji=emoji,
                    exchange_name=str(exchange.name),
                    pair=pair,
                )

                tg.create_task(self._send(message=message))

    async def send_anomaly_cancellation_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        await self.__send_anomaly_detection(
            anomalies=anomalies,
            emoji=CANCELLATION_EMOJI,
            destiny=AnomalyState.CANCELLED,
            pair_id=pair_id,
        )

    async def send_anomaly_realization_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        await self.__send_anomaly_detection(
            anomalies=anomalies,
            emoji=REALIZATION_EMOJI,
            destiny=AnomalyState.REALIZED,
            pair_id=pair_id,
        )

    def __prepare_message(
        self,
        anomaly: OrderAnomalyNotification,
        destiny: AnomalyState,
        emoji: str,
        pair: PairModel,
        exchange_name: str,
    ) -> BaseMessage:
        formatted_notification = self._format_anomaly_fields(
            anomaly=anomaly,
            exchange_name=exchange_name,
            pair_symbol=pair.symbol,
        )

        base_token = pair.symbol.split("/")[0]
        pair_token = pair.symbol.split("/")[1]

        description = (
            f"{emoji} #{formatted_notification.pair_symbol} #ORDERS "
            f"#{formatted_notification.upper_case_exchange_name}\n"
            f"{formatted_notification.quantity} *{base_token}* "
            f"({formatted_notification.order_liquidity} *{pair_token}*) anomaly *{anomaly.type}* "
            f"was {destiny.value} on {formatted_notification.title_case_exchange_name}"
        )

        fields = [
            Field(
                name="Average liquidity",
                value=formatted_notification.liquidity,
                inline=False,
            ),
            Field(
                name="Price", value=formatted_notification.price, inline=False
            ),
        ]

        return BaseMessage(description=description, fields=fields)

    def _format_anomaly_fields(
        self,
        anomaly: OrderAnomalyNotification,
        exchange_name: str,
        pair_symbol: str,
    ) -> FormattedMessage:
        formatted_quantity = add_comma_every_n_symbols(
            f"{anomaly.quantity: .2f}"
        )
        formatted_liquidity = add_comma_every_n_symbols(
            f"{anomaly.average_liquidity: .2f}"
        )
        formatted_order_liquidity = add_comma_every_n_symbols(
            f"{anomaly.order_liquidity: .2f}"
        )
        formatted_price = add_comma_every_n_symbols(
            round_decimal_to_first_non_zero(anomaly.price)
        )
        formatted_upper_case_exchange_name = to_upper_case(exchange_name)
        formatted_title_case_exchange_name = to_title_case(exchange_name)
        formatted_pair_symbol = replace_char(pair_symbol, "/", "")

        return FormattedMessage(
            quantity=formatted_quantity,
            liquidity=formatted_liquidity,
            order_liquidity=formatted_order_liquidity,
            price=formatted_price,
            upper_case_exchange_name=formatted_upper_case_exchange_name,
            title_case_exchange_name=formatted_title_case_exchange_name,
            pair_symbol=formatted_pair_symbol,
        )

    def __choose_appropriate_emoji(self, anomaly_type: str) -> str:
        return ASK_EMOJI if anomaly_type == "ask" else BID_EMOJI
