from typing import Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.exchange import ExchangeModel
from app.infrastructure.db.models.pair import PairModel


async def find_pair_by_id(session: AsyncSession, id: UUID) -> PairModel:
    result = await session.execute(select(PairModel).where(PairModel.id == id))

    return result.scalar_one()


async def get_pair_and_exchange(
    session: AsyncSession,
    pair_id: UUID,
) -> Tuple[PairModel, ExchangeModel]:
    query = (
        select(PairModel, ExchangeModel)
        .where(PairModel.id == pair_id)
        .join(ExchangeModel, ExchangeModel.id == PairModel.exchange_id)
    )

    result = await session.execute(query)

    pair, exchange = result.one()

    return pair, exchange
