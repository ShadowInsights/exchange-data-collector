from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pair import PairModel


async def find_pair_by_id(session: AsyncSession, id: UUID) -> PairModel:
    result = await session.execute(select(PairModel).where(PairModel.id == id))

    return result.scalar_one()
