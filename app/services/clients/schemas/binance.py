from dataclasses import dataclass
from typing import Dict, List


@dataclass
class OrderBookEntry:
    price: str
    quantity: str


@dataclass
class OrderBookSnapshot:
    lastUpdateId: int
    bids: Dict[str, str]
    asks: Dict[str, str]


@dataclass
class DepthUpdateEvent:
    event_type: str
    event_time: int
    symbol: str
    first_update_id: int
    final_update_id: int
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
