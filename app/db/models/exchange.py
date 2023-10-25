from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import BaseModel


class ExchangeModel(BaseModel):
    __tablename__ = "exchanges"

    name: Mapped[str] = mapped_column(
        String, nullable=False, index=True, unique=True
    )
