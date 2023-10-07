from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.pair import PairModel


async def find_all_pairs(session: AsyncSession) -> list[PairModel]:
    result = await session.execute(select(PairModel))
    return result.scalars().all()


async def find_pair_by_id(session: AsyncSession, id: UUID) -> PairModel:
    result = await session.execute(select(PairModel).where(PairModel.id == id))

    return result.scalar_one_or_none()
