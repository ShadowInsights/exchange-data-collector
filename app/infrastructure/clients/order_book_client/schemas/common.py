from abc import ABC
from dataclasses import dataclass

from _decimal import Decimal

from app.infrastructure.clients.common import Event, EventTypeEnum


@dataclass
class OrderBook(ABC):
    a: dict[Decimal, Decimal]
    b: dict[Decimal, Decimal]


class OrderBookEvent(Event):
    b: dict[Decimal, Decimal]
    a: dict[Decimal, Decimal]


class OrderBookSnapshot(OrderBookEvent):
    event_type: EventTypeEnum = EventTypeEnum.INIT


class OrderBookUpdate(OrderBookEvent):
    event_type: EventTypeEnum = EventTypeEnum.UPDATE
