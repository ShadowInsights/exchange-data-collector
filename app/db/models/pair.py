from decimal import Decimal
from uuid import UUID

from sqlalchemy import DECIMAL, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import BaseModel


class PairModel(BaseModel):
    __tablename__ = "pairs"

    symbol: Mapped[str] = mapped_column(
        String, nullable=False, index=True, unique=True
    )
    delimiter: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    exchange_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("exchanges.id"), nullable=False
    )
    maestro_instance_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True),
        ForeignKey("maestro_instances.id"),
        nullable=True,
    )
