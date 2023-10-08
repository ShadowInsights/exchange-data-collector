from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.common.database import BaseModel


class Liquidity(BaseModel):
    __tablename__ = "liquidity"

    average_volume = Column(Integer, nullable=False)
    launch_id = Column(UUID, nullable=False, index=True)
    pair_id = Column(
        UUID(as_uuid=True), ForeignKey("pairs.id"), nullable=False
    )
