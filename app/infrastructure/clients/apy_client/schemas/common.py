from abc import ABC
from dataclasses import dataclass
from decimal import Decimal

from app.infrastructure.clients.common import Event, EventTypeEnum


@dataclass
class APY(ABC):
    apy: Decimal


class APYEvent(Event):
    apy: Decimal


class APYSnapshot(APYEvent):
    event_type: EventTypeEnum = EventTypeEnum.INIT


class APYUpdate(APYEvent):
    event_type: EventTypeEnum = EventTypeEnum.UPDATE
