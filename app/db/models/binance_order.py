import uuid

from db.database import Base
from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Integer,
                        String, func)
from sqlalchemy.dialects.postgresql import UUID


class BinanceOrderModel(Base):
    __tablename__ = "binance_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String)
    binance_id = Column(Integer, index=True)
    price = Column(Float)
    qty = Column(Float)
    quote_qty = Column(Float)
    time = Column(BigInteger)
    is_buyer_maker = Column(Boolean)
    is_best_match = Column(Boolean)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
