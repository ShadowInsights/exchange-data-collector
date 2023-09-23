from sqlalchemy import Column, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import BaseModel


class OrderBookModel(BaseModel):
    __tablename__ = "order_books"

    launch_id = Column(UUID, nullable=False, index=True)
    stamp_id = Column(BigInteger, nullable=False, index=True)
    order_book = Column(JSONB, nullable=False)
    pair_id = Column(
        UUID(as_uuid=True), ForeignKey("pairs.id"), nullable=False
    )
