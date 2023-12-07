from abc import ABC, abstractmethod


class Field:
    def __init__(self, name: str, value: str, inline: bool):
        self.name = name
        self.value = value
        self.inline = inline


class BaseMessage:
    def __init__(
        self,
        description: str,
        fields: list[Field],
        title: str | None = None,
    ):
        self.title = title
        self.description = description
        self.fields = fields


class BaseMessenger(ABC):
    @abstractmethod
    async def _send(self, message: BaseMessage, **kwargs: str | int) -> None:
        pass
