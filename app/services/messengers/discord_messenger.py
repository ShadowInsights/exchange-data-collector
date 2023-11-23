import asyncio
import logging

from discord_webhook import AsyncDiscordWebhook, DiscordEmbed

from app.common.config import settings
from app.services.messengers.common import BaseMessage, BaseMessenger


class DiscordMessenger(BaseMessenger):
    def __init__(self) -> None:
        super().__init__()
        self.lock = asyncio.Lock()
        self.webhooks: list[AsyncDiscordWebhook] = [
            AsyncDiscordWebhook(
                webhook_url, rate_limit_retry=True, username="Anomaly Alerting"
            )
            for webhook_url in settings.DISCORD_WEBHOOKS.split(",")
        ]

    async def _send(
        self, message: BaseMessage, embed_color: str | int
    ) -> None:
        try:
            async with self.lock:
                webhook = self.webhooks.pop(0)
                self.webhooks.append(webhook)

                webhook.add_embed(
                    self._generate_message(
                        message=message, embed_color=embed_color
                    )
                )

                await webhook.execute(remove_embeds=True)
        except Exception as error:
            logging.error(f"Error while sending alert notification: {error}")

    def _generate_message(
        self, message: BaseMessage, embed_color: str | int
    ) -> DiscordEmbed:
        embed = DiscordEmbed(
            title=message.title,
            description=message.description,
            color=embed_color,
        )
        embed.set_timestamp()
        embed.set_footer(text="Shadow Insights")

        for field in message.fields:
            embed.add_embed_field(
                name=field.name, value=field.value, inline=field.inline
            )

        return embed
