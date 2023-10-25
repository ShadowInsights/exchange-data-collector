from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import BaseModel


class OrderBookModel(BaseModel):
    __tablename__ = "order_books"

    launch_id: Mapped[UUID] = mapped_column(
        pg_UUID, nullable=False, index=True
    )
    stamp_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    order_book: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pair_id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), ForeignKey("pairs.id"), nullable=False
    )
