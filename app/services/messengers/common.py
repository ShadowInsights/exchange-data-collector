from abc import ABC, abstractmethod


class Field:
    def __init__(self, name: str, value: str, inline: bool):
        self.name = name
        self.value = value
        self.inline = inline


class BaseMessage:
    def __init__(self, title: str, description: str, fields: list[Field]):
        self.title = title
        self.description = description
        self.fields = fields


class BaseMessenger(ABC):
    @abstractmethod
    async def _send(self, data: BaseMessage, embed_color: int) -> None:
        pass
