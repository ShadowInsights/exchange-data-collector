from uuid import UUID

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.liquidity import Liquidity


async def find_last_n_liquidity(
    session: AsyncSession, pair_id: UUID, amount: int
) -> list[Liquidity]:
    condition = text("pair_id = :pair_id").bindparams(pair_id=pair_id)

    result = await session.execute(
        select(Liquidity)
        .where(condition)
        .order_by(desc(Liquidity.created_at))
        .limit(amount)
    )

    return result.scalars().all()


async def save_liquidity(
    session: AsyncSession, avg_volume: float, launch_id: UUID, pair_id: UUID
) -> Liquidity:
    liquidity = Liquidity(
        average_volume=avg_volume, launch_id=launch_id, pair_id=pair_id
    )

    session.add(liquidity)

    return liquidity


async def save_all_liquidity(
    session: AsyncSession, liquidity_records: list[Liquidity]
) -> list[Liquidity]:
    for record in liquidity_records:
        session.add(record)

    return liquidity_records
