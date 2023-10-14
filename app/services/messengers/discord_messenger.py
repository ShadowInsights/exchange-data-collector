import asyncio
import logging

from discord_webhook import AsyncDiscordWebhook, DiscordEmbed

from app.common.config import settings
from app.services.messengers.base_messenger import BaseMessenger
from app.services.messengers.common import BaseMessage


class DiscordMessenger(BaseMessenger):
    def __init__(self, embed_color: str):
        super().__init__()
        self.lock = asyncio.Lock()
        self.webhooks = [
            AsyncDiscordWebhook(
                webhook_url, rate_limit_retry=True, username="Anomaly Alerting"
            )
            for webhook_url in settings.DISCORD_WEBHOOKS.split(",")
        ]
        self._embed_color = embed_color

    async def send(self, message: BaseMessage) -> None:
        try:
            async with self.lock:
                webhook = self.webhooks.pop(0)
                self.webhooks.append(webhook)

                webhook.add_embed(self._generate_message(message=message))

                await webhook.execute(remove_embeds=True)
        except Exception as error:
            logging.error(f"Error while sending alert notification: {error}")

    def _generate_message(self, message: BaseMessage) -> DiscordEmbed:
        embed = DiscordEmbed(
            title=message.title,
            description=message.description,
            color=self._embed_color,
        )
        embed.set_timestamp()

        for field in message.fields:
            embed.add_embed_field(
                name=field.name, value=field.value, inline=True
            )

        return embed
