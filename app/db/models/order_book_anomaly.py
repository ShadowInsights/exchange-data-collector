from typing import Literal
from uuid import UUID

from _decimal import Decimal
from sqlalchemy import DECIMAL, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import BaseModel


class OrderBookAnomalyModel(BaseModel):
    __tablename__ = "order_book_anomalies"

    launch_id: Mapped[UUID] = mapped_column(
        pg_UUID, nullable=False, index=True
    )
    pair_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("pairs.id"), nullable=False
    )
    price: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    order_liquidity: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    average_liquidity: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[Literal["ask", "bid"]] = mapped_column(nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(nullable=True)
