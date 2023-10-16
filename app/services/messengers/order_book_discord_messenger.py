import asyncio
from decimal import Decimal
from typing import Literal, NamedTuple
from uuid import UUID

from app.common.config import settings
from app.common.database import get_async_db
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.pair_repository import find_pair_by_id
from app.services.messengers.common import BaseMessage, Field
from app.services.messengers.discord_messenger import DiscordMessenger
from app.utils.string_utils import (add_comma_every_n_symbols,
                                    round_decimal_to_first_non_zero,
                                    to_title_case)


class OrderAnomalyNotification(NamedTuple):
    price: Decimal
    quantity: Decimal
    order_liquidity: Decimal
    average_liquidity: Decimal
    type: Literal["ask", "bid"]


class OrderBookDiscordMessenger(DiscordMessenger):
    def __init__(self):
        super().__init__()

    async def send_notifications(
        self, anomalies: list[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        # XXX: not the best way to get exchange name
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)

        title = "Order Anomaly"
        for anomaly in anomalies:
            formatted_price = add_comma_every_n_symbols(
                round_decimal_to_first_non_zero(anomaly.price)
            )
            formatted_quantity = add_comma_every_n_symbols(
                "{:.2f}".format(anomaly.quantity)
            )
            formatted_exchange_name = to_title_case(exchange.name)
            description = (
                f"Order anomaly {anomaly.type} was detected "
                f"for **{pair.symbol}** on **{formatted_exchange_name}**"
            )
            order_field = Field(
                name="Order",
                value=f"Price: {formatted_price}\nQuantity: "
                f"{formatted_quantity}",
            )
            average_liquidity_field = Field(
                name="Average liquidity",
                value=add_comma_every_n_symbols(
                    "{:.2f}".format(anomaly.average_liquidity)
                ),
            )
            order_liquidity_field = Field(
                name="Order liquidity",
                value=add_comma_every_n_symbols(
                    "{:.2f}".format(anomaly.order_liquidity)
                ),
            )
            message = BaseMessage(
                title=title,
                description=description,
                fields=[
                    order_field,
                    order_liquidity_field,
                    average_liquidity_field,
                ],
            )
            if anomaly.type == "ask":
                asyncio.create_task(
                    self._send(
                        message=message,
                        embed_color=settings.DISCORD_ORDER_ANOMALY_ASK_EMBED_COLOR,
                    )
                )
            elif anomaly.type == "bid":
                asyncio.create_task(
                    self._send(
                        message=message,
                        embed_color=settings.DISCORD_ORDER_ANOMALY_BID_EMBED_COLOR,
                    )
                )
