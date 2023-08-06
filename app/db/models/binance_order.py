from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass
class BinanceOrderModel:
    id: UUID
    launch_id: UUID
    order_type: int
    price: Decimal
    quantity: Decimal
    bucket_id: UUID
    pair_id: int
    exchange_id: int
    stamp_id: int
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "BinanceOrderModel":
        return cls(
            id=UUID(data["id"]),
            launch_id=UUID(data["launch_id"]),
            order_type=data["order_type"],
            price=Decimal(data["price"]),
            quantity=data["quantity"],
            bucket_id=UUID(data["bucket_id"]),
            pair_id=data["pair_id"],
            exchange_id=data["exchange_id"],
            stamp_id=data["stamp_id"],
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "launch_id": self.launch_id,
            "order_type": self.order_type,
            "price": self.price,
            "quantity": self.quantity,
            "bucket_id": self.bucket_id,
            "pair_id": self.pair_id,
            "exchange_id": self.exchange_id,
            "stamp_id": self.stamp_id,
            "created_at": self.created_at,
        }
