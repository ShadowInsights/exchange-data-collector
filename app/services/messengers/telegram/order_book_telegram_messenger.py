import asyncio
from typing import List, Tuple
from uuid import UUID

from app.common.database import get_async_db
from app.db.models.exchange import ExchangeModel
from app.db.models.pair import PairModel
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.pair_repository import find_pair_by_id
from app.services.messengers.common import BaseMessage, Field
from app.services.messengers.discord.order_book_discord_messenger import (
    OrderAnomalyNotification,
)
from app.services.messengers.order_book_messenger import OrderBookMessenger
from app.services.messengers.telegram.telegram_messenger import TelegramMessenger
from app.utils.string_utils import add_comma_every_n_symbols, replace_char

BID_EMOJI = "📉"
ASK_EMOJI = "📈"
CANCELLATION_EMOJI = "✖"
REALIZATION_EMOJI = "✔️"


class OrderBookTelegramMessenger(OrderBookMessenger, TelegramMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def __send_anomaly_detection(
        self,
        anomalies: List[OrderAnomalyNotification],
        emoji: str,
        destiny: str,
        pair_id: UUID,
    ) -> None:
        exchange, pair = await self._get_exchange_and_pair(pair_id=pair_id)

        async with asyncio.TaskGroup() as tg:
            for anomaly in anomalies:
                message = self.__prepare_message(
                    anomaly=anomaly,
                    destiny=destiny,
                    emoji=emoji,
                    exchange=exchange,
                    pair=pair,
                )

                tg.create_task(self._send(message=message))

    async def send_anomaly_detection_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        exchange, pair = await self._get_exchange_and_pair(pair_id=pair_id)

        async with asyncio.TaskGroup() as tg:
            for anomaly in anomalies:
                emoji = ASK_EMOJI if anomaly.type == "ask" else BID_EMOJI

                message = self.__prepare_message(
                    anomaly=anomaly,
                    destiny="detected",
                    emoji=emoji,
                    exchange=exchange,
                    pair=pair,
                )

                tg.create_task(self._send(message=message))

    async def send_anomaly_cancellation_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        await self.__send_anomaly_detection(
            anomalies=anomalies,
            emoji=CANCELLATION_EMOJI,
            destiny="CANCELLED",
            pair_id=pair_id,
        )

    async def send_anomaly_realization_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        await self.__send_anomaly_detection(
            anomalies=anomalies,
            emoji=REALIZATION_EMOJI,
            destiny="REALIZED",
            pair_id=pair_id,
        )

    async def _get_exchange_and_pair(
        self, pair_id: UUID
    ) -> Tuple[ExchangeModel, PairModel]:
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)
        return exchange, pair

    def __prepare_message(
        self,
        anomaly: OrderAnomalyNotification,
        destiny: str,
        emoji: str,
        pair: PairModel,
        exchange: ExchangeModel,
    ) -> BaseMessage:
        [
            formatted_quantity,
            formatted_liquidity,
            formatted_order_liquidity,
        ] = self._format_anomaly_fields(anomaly=anomaly)

        base_token = pair.symbol.split("/")[0]
        pair_token = pair.symbol.split("/")[1]
        formatted_pair = replace_char(pair.symbol, "/", "")

        description = (
            f"{emoji} {formatted_quantity} #{base_token} ({formatted_order_liquidity} #{pair_token})"
            f" anomaly {anomaly.type} was {destiny} #{exchange.name} #{formatted_pair}"
        )

        fields = [
            Field(
                name="Average liquidity",
                value=formatted_liquidity,
                inline=False,
            )
        ]

        return BaseMessage(description=description, fields=fields)

    def _format_anomaly_fields(
        self, anomaly: OrderAnomalyNotification
    ) -> Tuple[str, str, str]:
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
            formatted_quantity,
            formatted_liquidity,
            formatted_order_liquidity,
        )
