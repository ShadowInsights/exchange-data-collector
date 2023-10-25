from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import BaseModel
from app.db.models.pair import PairModel


class MaestroInstanceModel(BaseModel):
    __tablename__ = "maestro_instances"

    launch_id: Mapped[UUID] = mapped_column(
        pg_UUID, nullable=False, index=True
    )
    latest_liveness_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    pairs: Mapped[list[PairModel]] = relationship()
