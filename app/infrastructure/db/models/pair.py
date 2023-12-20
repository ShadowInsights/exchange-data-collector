from uuid import UUID

from _decimal import Decimal
from sqlalchemy import DECIMAL, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.database import BaseModel


class PairModel(BaseModel):
    __tablename__ = "pairs"

    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    delimiter: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    exchange_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("exchanges.id"), nullable=False
    )
