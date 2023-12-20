from abc import ABC
from enum import Enum

from pydantic import BaseModel


class CoinbaseOrderType(Enum):
    BUY = "buy"
    SELL = "sell"


class CoinbaseEventType(Enum):
    SNAPSHOT = "snapshot"
    UPDATE = "l2update"


class CoinbaseOrderBook(BaseModel, ABC):
    pass


class CoinbaseSnapshotPayload(BaseModel):
    product_ids: list[str] = []
    channels: list[str] = []
    type: str = "subscribe"


class CoinbaseOrderBookSnapshot(CoinbaseOrderBook):
    type: str
    product_id: str
    bids: list
    asks: list


class CoinbaseOrderBookDepthUpdate(CoinbaseOrderBook):
    type: str
    product_id: str
    time: str
    changes: list
