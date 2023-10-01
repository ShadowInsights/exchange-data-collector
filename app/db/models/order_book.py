from sqlalchemy import BigInteger, Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.common.database import BaseModel


class OrderBookModel(BaseModel):
    __tablename__ = "order_books"

    launch_id = Column(UUID, nullable=False, index=True)
    stamp_id = Column(BigInteger, nullable=False, index=True)
    order_book = Column(JSONB, nullable=False)
    pair_id = Column(
        UUID(as_uuid=True), ForeignKey("pairs.id"), nullable=False
    )
