from decimal import Decimal

from pydantic import BaseModel


class OrderBook(BaseModel):
    a: dict[Decimal, Decimal]
    b: dict[Decimal, Decimal]
