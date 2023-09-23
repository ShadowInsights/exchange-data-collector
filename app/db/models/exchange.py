from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.db.database import BaseModel


class ExchangeModel(BaseModel):
    __tablename__ = "exchanges"

    name = Column(String, nullable=False, index=True, unique=True)
