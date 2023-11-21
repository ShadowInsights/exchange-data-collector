from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.models.volume import Volume


async def find_last_n_volumes(
    session: AsyncSession, pair_id: UUID, amount: int
) -> list[Volume]:
    result = await session.execute(
        select(Volume)
        .where(Volume.pair_id == pair_id)
        .order_by(desc(Volume.created_at))
        .limit(amount)
    )

    return result.scalars().all()


def find_sync_last_n_volumes(
    session: Session, pair_id: UUID, amount: int
) -> list[Volume]:
    return (
        session.query(Volume)
        .where(Volume.pair_id == pair_id)
        .order_by(desc(Volume.created_at))
        .limit(amount)
        .all()
    )


async def save_volume(
    session: AsyncSession,
    bid_ask_ratio: float,
    avg_volume: int,
    launch_id: UUID,
    pair_id: UUID,
) -> Volume:
    liquidity = Volume(
        bid_ask_ratio=bid_ask_ratio,
        average_volume=avg_volume,
        launch_id=launch_id,
        pair_id=pair_id,
    )

    session.add(liquidity)

    return liquidity


async def save_all_volumes(
    session: AsyncSession, liquidity_records: list[Volume]
) -> list[Volume]:
    session.add_all(liquidity_records)

    return liquidity_records
