from decimal import Decimal
from uuid import UUID

from sqlalchemy import DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import BaseModel


class OrdersAnomaliesSummaryModel(BaseModel):
    __tablename__ = "orders_anomalies_summaries"

    launch_id: Mapped[UUID] = mapped_column(
        pg_UUID, nullable=False, index=True
    )
    pair_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("pairs.id"), nullable=False
    )
    orders_total_difference: Mapped[Decimal] = mapped_column(
        DECIMAL, nullable=False
    )
