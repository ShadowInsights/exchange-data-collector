from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import BaseModel


class Volume(BaseModel):
    __tablename__ = "volumes"

    bid_ask_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    average_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    launch_id: Mapped[UUID] = mapped_column(
        pg_UUID, nullable=False, index=True
    )
    pair_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("pairs.id"), nullable=False
    )
