import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from sqlalchemy import Column, DateTime, text
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from app.common.config import DB_CONNECTION_STRING_ASYNC

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    DB_CONNECTION_STRING_ASYNC,
    echo=False,
)


@asynccontextmanager
async def get_db() -> AsyncIterator[AsyncSession]:
    session_class = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
    )
    session = session_class()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


class BaseModel(DeclarativeBase):
    id = Column(pg_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(
        DateTime, nullable=False, server_default=text("current_timestamp(0)")
    )
