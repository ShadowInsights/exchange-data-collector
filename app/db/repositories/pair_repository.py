from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.maestro import MaestroInstanceModel
from app.db.models.pair import PairModel


async def find_all_not_collecting_pairs_for_update(
    session: AsyncSession, liveness_time_interval: datetime
) -> list[PairModel]:
    no_maestro_pairs = await session.execute(
        select(PairModel)
        .where(PairModel.maestro_instance_id.is_(None))
        .limit(1)
    )

    if no_maestro_pairs.scalar_one_or_none():
        query = select(PairModel).where(
            PairModel.maestro_instance_id.is_(None)
        )
    else:
        oldest_maestro_pair_query = (
            select(PairModel)
            .join(MaestroInstanceModel)
            .where(
                MaestroInstanceModel.latest_liveness_time
                < liveness_time_interval
            )
            .order_by(MaestroInstanceModel.latest_liveness_time.asc())
            .limit(1)
        )
        oldest_maestro_pair = await session.scalar(oldest_maestro_pair_query)
        if not oldest_maestro_pair:
            return []

        query = select(PairModel).where(
            PairModel.maestro_instance_id
            == oldest_maestro_pair.maestro_instance_id
        )

    result = await session.execute(query.with_for_update())
    return result.scalars().all()


async def update_pairs_maestro_id(
    session: AsyncSession,
    pairs: list[PairModel],
    maestro_id: UUID,
    commit: bool = True,
) -> None:
    for pair in pairs:
        pair.maestro_instance_id = maestro_id

    if commit:
        await session.commit()


async def find_pair_by_id(session: AsyncSession, id: UUID) -> PairModel:
    result = await session.execute(select(PairModel).where(PairModel.id == id))

    return result.scalar_one_or_none()


async def find_all_pairs_by_maestro_id(
    session: AsyncSession, maestro_id: UUID
) -> list[PairModel]:
    result = await session.execute(
        select(PairModel).where(PairModel.maestro_instance_id == maestro_id)
    )

    return result.scalars().all()
