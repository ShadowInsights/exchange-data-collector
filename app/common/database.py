import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Iterator
from uuid import uuid4

from sqlalchemy import Column, DateTime, create_engine, text
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.common.config import DB_CONNECTION_STRING, DB_CONNECTION_STRING_ASYNC

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    DB_CONNECTION_STRING_ASYNC,
    echo=False,
)
engine = create_engine(DB_CONNECTION_STRING)


@asynccontextmanager
async def get_async_db() -> AsyncIterator[AsyncSession]:
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


@contextmanager
def get_sync_db() -> Iterator[Session]:
    session_class = sessionmaker(bind=engine)
    session = session_class()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class BaseModel(DeclarativeBase):
    id = Column(pg_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(
        DateTime, nullable=False, server_default=text("current_timestamp(0)")
    )
