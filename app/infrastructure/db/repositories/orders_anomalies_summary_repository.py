from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.orders_anomalies_summary import (
    OrdersAnomaliesSummaryModel,
)


async def create_orders_anomalies_summary(
    session: AsyncSession,
    orders_anomalies_summary_in: OrdersAnomaliesSummaryModel,
    commit: bool = True,
) -> OrdersAnomaliesSummaryModel:
    session.add(orders_anomalies_summary_in)
    if commit:
        await session.commit()
    return orders_anomalies_summary_in


async def get_latest_orders_anomalies_summary(
    session: AsyncSession,
    pair_id: UUID,
    limit: int,
) -> Sequence[OrdersAnomaliesSummaryModel]:
    return (
        (
            await session.execute(
                select(OrdersAnomaliesSummaryModel)
                .where(OrdersAnomaliesSummaryModel.pair_id == pair_id)
                .order_by(OrdersAnomaliesSummaryModel.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
