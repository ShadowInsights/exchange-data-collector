import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, create_engine, text
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from app.common.config import (
    DB_CONNECTION_STRING,
    DB_CONNECTION_STRING_ASYNC,
    settings,
)

logger = logging.getLogger(__name__)

async_engine = create_async_engine(
    DB_CONNECTION_STRING_ASYNC,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
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
    id: Mapped[UUID] = mapped_column(
        pg_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("current_timestamp(0)")
    )
