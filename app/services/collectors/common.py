from decimal import Decimal

from pydantic import BaseModel

from app.utils.time_utils import (LONDON_TRADING_SESSION,
                                  NEW_YORK_TRADING_SESSION,
                                  TOKYO_TRADING_SESSION)

trading_sessions = [
    TOKYO_TRADING_SESSION,
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
]


class OrderBook(BaseModel):
    a: dict[Decimal, Decimal]
    b: dict[Decimal, Decimal]
