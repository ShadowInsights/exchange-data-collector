from app.application.messengers.volume_messenger import (VolumeMessenger,
                                                         VolumeNotification)
from app.config import settings
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.repositories.pair_repository import \
    get_pair_and_exchange
from app.infrastructure.messengers.common import BaseMessage, Field
from app.infrastructure.messengers.discord_messenger import DiscordMessenger
from app.utilities.string_utils import add_comma_every_n_symbols, to_title_case


class VolumeDiscordMessenger(VolumeMessenger, DiscordMessenger):
    def __init__(self) -> None:
        super().__init__()

    async def send_notification(
        self, notification: VolumeNotification
    ) -> None:
        async with get_async_db() as session:
            pair, exchange = await get_pair_and_exchange(
                session=session, pair_id=notification.pair_id
            )

        # Formatting message
        title = "Depth Anomaly"

        if notification.deviation < 1:
            depth_change_vector = "Decreased"
        else:
            depth_change_vector = "Increased"

        formatted_exchange_name = to_title_case(str(exchange.name))
        description = f"{depth_change_vector} depth was detected for **{pair.symbol}** on **{formatted_exchange_name}**"
        deviation_field = Field(
            name="Deviation",
            value="{:.2f}".format(notification.deviation),
            inline=True,
        )
        volume_changes_field = Field(
            name="Depth changes",
            value=f"Current: {add_comma_every_n_symbols(notification.current_avg_volume)}\nPrevious: "
            f"{add_comma_every_n_symbols(notification.previous_avg_volume)}",
            inline=True,
        )
        ask_bid_ratio_changes_field = Field(
            name="Bid & Ask ratio",
            value=f"Current: {add_comma_every_n_symbols(notification.current_bid_ask_ratio)}\nPrevious: "
            f"{add_comma_every_n_symbols(notification.previous_bid_ask_ratio)}",
            inline=True,
        )

        # Construct message to send
        message = BaseMessage(
            title=title,
            description=description,
            fields=[
                deviation_field,
                volume_changes_field,
                ask_bid_ratio_changes_field,
            ],
        )

        # Sending message
        await self._send(
            message=message, embed_color=settings.DISCORD_DEPTH_EMBED_COLOR
        )
