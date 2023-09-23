from sqlalchemy import DECIMAL, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import BaseModel


class PairModel(BaseModel):
    __tablename__ = "pairs"

    symbol = Column(String, nullable=False, index=True, unique=True)
    delimiter = Column(DECIMAL, nullable=False)
    exchange_id = Column(
        UUID(as_uuid=True), ForeignKey("exchanges.id"), nullable=False
    )
