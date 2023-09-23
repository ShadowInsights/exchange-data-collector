from sqlalchemy import Column, String

from app.db.common import BaseModel


class ExchangeModel(BaseModel):
    __tablename__ = "exchanges"

    name = Column(String, nullable=False, index=True, unique=True)
