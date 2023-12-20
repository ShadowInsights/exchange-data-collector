from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
)

from app.infrastructure.db.database import BaseModel
from app.infrastructure.db.models.pair import PairModel

Base = declarative_base()

maestro_pair_association = Table(
    "maestro_pair_association",
    BaseModel.metadata,
    Column(
        "maestro_instance_id",
        pg_UUID(as_uuid=True),
        ForeignKey("maestro_instances.id"),
        primary_key=True,
    ),
    Column(
        "pair_id",
        pg_UUID(as_uuid=True),
        ForeignKey("pairs.id"),
        primary_key=True,
    ),
)


class MaestroInstanceModel(BaseModel):
    __tablename__ = "maestro_instances"

    launch_id: Mapped[UUID] = mapped_column(
        pg_UUID, nullable=False, index=True
    )
    latest_liveness_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    pairs: Mapped[list[PairModel]] = relationship(
        secondary=maestro_pair_association, backref="maestro_instance"
    )
