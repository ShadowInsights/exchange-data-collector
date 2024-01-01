from uuid import UUID

from _decimal import Decimal
from sqlalchemy import DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.database import BaseModel


class APY(BaseModel):
    __tablename__ = "apy"

    apy: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    launch_id: Mapped[UUID] = mapped_column(
        pg_UUID, nullable=False, index=True
    )
    apy_asset_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("apy_asset.id"), nullable=False
    )
