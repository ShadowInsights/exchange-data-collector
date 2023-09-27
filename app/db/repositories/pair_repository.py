from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.pair import PairModel


async def find_all_pairs(session: AsyncSession) -> list[PairModel]:
    result = await session.execute(select(PairModel))
    return result.scalars().all()
