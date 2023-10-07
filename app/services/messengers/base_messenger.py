from abc import ABC, abstractmethod

from app.services.messengers.common import BaseMessage


class BaseMessenger(ABC):
    @abstractmethod
    async def send(self, data: BaseMessage):
        pass
