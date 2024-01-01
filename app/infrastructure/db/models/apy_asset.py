from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.database import BaseModel


class APYAsset(BaseModel):
    __tablename__ = "apy_asset"

    symbol: Mapped[str] = mapped_column(String, nullable=False)
    exchange_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("exchanges.id"), nullable=False
    )
