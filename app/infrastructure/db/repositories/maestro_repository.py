from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.maestro import (MaestroInstanceModel,
                                                  maestro_pair_association)
from app.infrastructure.db.models.pair import PairModel


class PairsForUpdateResult(NamedTuple):
    pair_ids: list[UUID]


class CollectingPairsForUpdateResult(NamedTuple):
    pair_ids: list[UUID]
    attached_maestro_id: UUID


async def create_maestro(
    session: AsyncSession, launch_id: UUID
) -> MaestroInstanceModel:
    maestro = MaestroInstanceModel(
        launch_id=launch_id, latest_liveness_time=datetime.now()
    )
    session.add(maestro)
    return maestro


async def update_maestro_liveness_time(
    session: AsyncSession, maestro_id: UUID, commit: bool = True
) -> None:
    maestro = await session.get(MaestroInstanceModel, maestro_id)
    if maestro:
        maestro.latest_liveness_time = datetime.utcnow()
        if commit:
            await session.commit()


async def find_all_not_collecting_pairs_for_update(
    session: AsyncSession, liveness_time_interval: datetime
) -> PairsForUpdateResult | CollectingPairsForUpdateResult:
    associated_pairs_subquery = select(
        maestro_pair_association.c.pair_id
    ).subquery()
    no_maestro_pairs = await session.execute(
        select(PairModel)
        .where(~PairModel.id.in_(select(associated_pairs_subquery)))
        .limit(1)
    )
    if no_maestro_pairs.scalar_one_or_none():
        query = (
            select(PairModel.id)
            .where(~PairModel.id.in_(select(associated_pairs_subquery)))
            .with_for_update()
        )

        raws = await session.execute(query)

        return PairsForUpdateResult(
            pair_ids=[row for row in raws.scalars().all()],
        )
    else:
        oldest_maestro_query = (
            select(maestro_pair_association.c.maestro_instance_id)
            .join(MaestroInstanceModel)
            .where(
                MaestroInstanceModel.latest_liveness_time
                < liveness_time_interval
            )
            .order_by(MaestroInstanceModel.latest_liveness_time.asc())
            .limit(1)
        ).with_for_update()

        old_maestro_id_result = await session.execute(oldest_maestro_query)
        old_maestro_id = old_maestro_id_result.scalar_one_or_none()

        if not old_maestro_id:
            return PairsForUpdateResult(pair_ids=[])

        query = (
            select(maestro_pair_association.c.pair_id)
            .where(
                maestro_pair_association.c.maestro_instance_id
                == old_maestro_id
            )
            .with_for_update()
        )
        raws = await session.execute(query)

        return CollectingPairsForUpdateResult(
            pair_ids=[row for row in raws.scalars().all()],
            attached_maestro_id=old_maestro_id,
        )


async def update_maestro_pair_associations(
    session: AsyncSession,
    old_maestro_id: UUID,
    new_maestro_id: UUID,
    commit: bool = True,
) -> None:
    await session.execute(
        maestro_pair_association.update()
        .where(
            maestro_pair_association.c.maestro_instance_id == old_maestro_id
        )
        .values(maestro_instance_id=new_maestro_id)
    )

    if commit:
        await session.commit()


async def create_maestro_pair_associations(
    session: AsyncSession,
    maestro_id: UUID,
    pair_ids: list[UUID],
    commit: bool = True,
) -> None:
    maestro_pair_associations = [
        {
            "maestro_instance_id": maestro_id,
            "pair_id": pair_id,
        }
        for pair_id in pair_ids
    ]
    await session.execute(
        maestro_pair_association.insert(), maestro_pair_associations
    )

    if commit:
        await session.commit()


async def delete_maestro_by_id(
    session: AsyncSession,
    maestro_id: UUID,
    commit: bool = True,
) -> None:
    stmt = delete(MaestroInstanceModel).where(
        MaestroInstanceModel.id == maestro_id
    )

    await session.execute(stmt)

    if commit:
        await session.commit()
