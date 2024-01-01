from decimal import Decimal

from app.application.messengers.apy_messenger import (APYMessenger,
                                                      APYNotification)
from app.application.messengers.common import define_trend_status_by_deviation
from app.config import settings
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.models.apy_asset import APYAsset
from app.infrastructure.db.repositories.apy_asset_repository import \
    get_apy_asset_and_exchange
from app.infrastructure.messengers.common import BaseMessage, Field
from app.infrastructure.messengers.discord_messenger import DiscordMessenger
from app.utilities.string_utils import add_comma_every_n_symbols, to_title_case

# Formatting message
TITLE = "APY Anomaly"


class APYDiscordMessenger(APYMessenger, DiscordMessenger):
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

        # Sending message
        await self._send(
            message=message, embed_color=settings.DISCORD_DEPTH_EMBED_COLOR
        )

    def __prepare_message(
        self,
        deviation: Decimal,
        current_apy: Decimal,
        previous_apy: Decimal,
        exchange_name: str,
        apy_asset: APYAsset,
    ) -> BaseMessage:
        apy_change_vector = define_trend_status_by_deviation(deviation)

        formatted_exchange_name = to_title_case(str(exchange_name))
        description = f"{apy_change_vector} apy was detected for **{apy_asset.symbol}** on **{formatted_exchange_name}**"
        deviation_field = Field(
            name="Deviation",
            value="{:.2f}".format(deviation),
            inline=True,
        )
        apy_changes_field = Field(
            name="APY changes",
            value=f"Current: {add_comma_every_n_symbols(current_apy)}\nPrevious: "
            f"{add_comma_every_n_symbols(previous_apy)}",
            inline=True,
        )

        # Construct message to send
        return BaseMessage(
            title=TITLE,
            description=description,
            fields=[
                deviation_field,
                apy_changes_field,
            ],
        )
