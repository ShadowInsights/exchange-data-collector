from typing import Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.apy_asset import APYAsset
from app.infrastructure.db.models.exchange import ExchangeModel


async def find_apy_asset_by_id(session: AsyncSession, id: UUID) -> APYAsset:
    result = await session.execute(select(APYAsset).where(APYAsset.id == id))

    return result.scalar_one()


async def get_apy_asset_and_exchange(
    session: AsyncSession,
    apy_asset_id: UUID,
) -> Tuple[APYAsset, ExchangeModel]:
    query = (
        select(APYAsset, ExchangeModel)
        .where(APYAsset.id == apy_asset_id)
        .join(ExchangeModel, ExchangeModel.id == APYAsset.exchange_id)
    )

    result = await session.execute(query)

    pair, exchange = result.one()

    return pair, exchange
