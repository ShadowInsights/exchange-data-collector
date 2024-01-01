from typing import Literal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.database import BaseModel

LiteralExchangeName = Mapped[Literal["BINANCE", "KRAKEN", "COINBASE"]]


class ExchangeModel(BaseModel):
    __tablename__ = "exchanges"

    name: Mapped[LiteralExchangeName] = mapped_column(
        String, nullable=False, index=True, unique=True
    )
