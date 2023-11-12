from _decimal import Decimal
from enum import Enum
from typing import Dict

from pydantic import BaseModel


class KrakenOrder(BaseModel):
    price: Decimal
    volume: Decimal
    timestamp: Decimal


class KrakenOrdersDict(BaseModel):
    a: list[KrakenOrder]
    b: list[KrakenOrder]


class KrakenOrderBook(BaseModel):
    channel_id: int
    orders: KrakenOrdersDict
    channel_name: str
    pair: str


class KrakenOrderBookSnapshot(KrakenOrderBook):
    pass


class KrakenOrderBookDepthUpdate(KrakenOrderBook):
    checksum: str


class KrakenSnapshotPayload(BaseModel):
    pair: list[str] = []
    subscription: Dict = {"name": "book", "depth": 100}
    event: str = "subscribe"


class KrakenEventType(Enum):
    INIT = "init"
    UPDATE = "update"
    NOT_SUPPORTED = "not_supported"
