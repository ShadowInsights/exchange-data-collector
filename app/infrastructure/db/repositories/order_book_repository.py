from typing import Sequence
from uuid import UUID

from sqlalchemy import DateTime, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.db.models.order_book import OrderBookModel


async def create_order_book(
    session: AsyncSession,
    launch_id: UUID,
    stamp_id: int,
    pair_id: UUID,
    order_book_json: str,
) -> OrderBookModel:
    order_book = OrderBookModel(
        launch_id=launch_id,
        stamp_id=stamp_id,
        pair_id=pair_id,
        order_book=order_book_json,
    )
    session.add(order_book)
    return order_book


async def find_all_between_time_range(
    session: AsyncSession,
    begin_time: DateTime,
    end_time: DateTime,
    pair_id: UUID,
) -> Sequence[OrderBookModel]:
    query = (
        select(OrderBookModel)
        .where(
            and_(
                OrderBookModel.created_at.between(begin_time, end_time),
                OrderBookModel.pair_id == pair_id,
            )
        )
        .order_by(asc(OrderBookModel.created_at))
    )

    result = await session.execute(query)

    return result.scalars().all()
