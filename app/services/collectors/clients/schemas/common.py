from abc import ABC
from dataclasses import dataclass
from enum import Enum

from _decimal import Decimal


@dataclass
class OrderBook(ABC):
    a: dict[Decimal, Decimal]
    b: dict[Decimal, Decimal]


class EventTypeEnum(Enum):
    INIT = "init"
    UPDATE = "update"


class OrderBookEvent(OrderBook):
    def __init__(
        self,
        event_type: EventTypeEnum,
        b: dict[Decimal, Decimal],
        a: dict[Decimal, Decimal],
    ):
        super().__init__(b=b, a=a)
        self.event_type = event_type


class OrderBookSnapshot(OrderBookEvent):
    def __init__(
        self,
        b: dict[Decimal, Decimal],
        a: dict[Decimal, Decimal],
    ):
        super().__init__(event_type=EventTypeEnum.INIT, b=b, a=a)


class OrderBookUpdate(OrderBookEvent):
    def __init__(
        self,
        b: dict[Decimal, Decimal],
        a: dict[Decimal, Decimal],
    ):
        super().__init__(event_type=EventTypeEnum.UPDATE, b=b, a=a)
