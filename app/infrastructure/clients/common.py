from abc import ABC
from enum import Enum

from pydantic import BaseModel

from app.utilities.string_utils import replace_char


class Client(ABC):
    def __init__(self, symbol: str, symbol_splitter: str):
        self.symbol = replace_char(symbol, "/", symbol_splitter)


class WebsocketClient(Client):
    def __init__(self, symbol: str, symbol_splitter: str):
        super().__init__(symbol, symbol_splitter)


class HttpClient(Client):
    def __init__(self, symbol: str, symbol_splitter: str):
        super().__init__(symbol, symbol_splitter)


class EventTypeEnum(Enum):
    INIT = "init"
    UPDATE = "update"


class Event(BaseModel):
    event_type: EventTypeEnum
