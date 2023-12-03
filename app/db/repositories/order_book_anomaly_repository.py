from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order_book_anomaly import OrderBookAnomalyModel


async def create_order_book_anomalies(
    session: AsyncSession,
    order_book_anomalies: list[OrderBookAnomalyModel],
) -> list[OrderBookAnomalyModel]:
    session.add_all(order_book_anomalies)
    return order_book_anomalies


async def merge_and_cancel_anomalies(
    session: AsyncSession, anomalies_to_cancel: list[OrderBookAnomalyModel]
) -> None:
    for anomaly in anomalies_to_cancel:
        merged_anomaly = await session.merge(anomaly)
        merged_anomaly.is_cancelled = True
    await session.commit()


async def merge_and_confirm_anomalies(
    session: AsyncSession, anomalies_to_confirm: list[OrderBookAnomalyModel]
) -> None:
    for anomaly in anomalies_to_confirm:
        merged_anomaly = await session.merge(anomaly)
        merged_anomaly.is_cancelled = False
    await session.commit()


async def get_order_book_anomalies_sum_in_date_range(
    session: AsyncSession,
    pair_id: UUID,
    start_datetime: datetime | None,
    end_datetime: datetime,
    type: Literal["ask", "bid"],
) -> Decimal:
    query = (
        select(func.sum(OrderBookAnomalyModel.order_liquidity))
        .where(OrderBookAnomalyModel.pair_id == pair_id)
        .where(OrderBookAnomalyModel.updated_at <= end_datetime)
        .where(OrderBookAnomalyModel.type == type)
    )
    if start_datetime is not None:
        query = query.where(OrderBookAnomalyModel.updated_at >= start_datetime)

    result = await session.execute(query)
    sum = result.scalar_one_or_none()

    return sum if sum is not None else Decimal(0)
