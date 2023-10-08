from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.models.liquidity import Liquidity


async def find_last_n_liquidity(
    session: AsyncSession, pair_id: UUID, amount: int
) -> list[Liquidity]:
    result = await session.execute(
        select(Liquidity)
        .where(Liquidity.pair_id == pair_id)
        .order_by(desc(Liquidity.created_at))
        .limit(amount)
    )

    return result.scalars().all()


def find_sync_last_n_liquidity(
    session: Session, pair_id: UUID, amount: int
) -> list[Liquidity]:
    return (
        session.query(Liquidity)
        .where(Liquidity.pair_id == pair_id)
        .order_by(desc(Liquidity.created_at))
        .limit(amount)
        .all()
    )


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
    session.add_all(liquidity_records)

    return liquidity_records
