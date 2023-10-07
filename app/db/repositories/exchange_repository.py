from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.exchange import ExchangeModel


async def find_exchange_by_id(
    session: AsyncSession, id: UUID
) -> ExchangeModel:
    result = await session.execute(
        select(ExchangeModel).where(ExchangeModel.id == id)
    )

    return result.scalar_one_or_none()
