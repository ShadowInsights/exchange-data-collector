import asyncio
import logging

import telegram
from telegram import Bot
from telegram.constants import ParseMode

from app.config import settings
from app.infrastructure.messengers.common import BaseMessage, BaseMessenger


class TelegramMessenger(BaseMessenger):
    def __init__(self) -> None:
        super().__init__()
        self.lock = asyncio.Lock()
        self.bots: list[Bot] = [
            telegram.Bot(token=token)
            for token in settings.TELEGRAM_BOT_TOKENS.split(",")
        ]
        self.chat_ids: list[str] = [
            identifier for identifier in settings.TELEGRAM_CHAT_IDS.split(",")
        ]

    async def _send(self, message: BaseMessage, **kwargs: str | int) -> None:
        try:
            async with self.lock:
                bot = self.bots.pop(0)
                self.bots.append(bot)

                for chat_id in self.chat_ids:
                    await bot.send_message(
                        chat_id=int(chat_id),
                        text=self._generate_message(message),
                        parse_mode=ParseMode.MARKDOWN,
                    )

        except Exception as error:
            logging.error(f"Error while sending alert notification: {error}")

    def _generate_message(self, message: BaseMessage) -> str:
        formatted_message = ""

        if message.title is not None:
            formatted_message += f"#{message.title}\n"

        formatted_message = f"{message.description}\n\n"

        for field in message.fields:
            formatted_message += f"*{field.name}*: {field.value} "
            if not field.inline:
                formatted_message += "\n"

        return formatted_message
