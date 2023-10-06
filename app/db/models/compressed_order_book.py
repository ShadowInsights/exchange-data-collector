from sqlalchemy import Column, Float, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.common.database import BaseModel


class CompressedOrderBook(BaseModel):
    __tablename__ = "compressed_order_books"

    average_volume = Column(Float, nullable=False)
    launch_id = Column(UUID, nullable=False, index=True)
    time_period = Column(Integer, nullable=False)
    pair_id = Column(UUID, nullable=False)
