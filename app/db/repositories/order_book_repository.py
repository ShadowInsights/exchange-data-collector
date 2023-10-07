from uuid import UUID

from sqlalchemy import DateTime, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.order_book import OrderBookModel


async def create_order_book(
    session: AsyncSession,
    launch_id: UUID,
    stamp_id: int,
    pair_id: UUID,
    order_book: str,
) -> OrderBookModel:
    order_book = OrderBookModel(
        launch_id=launch_id,
        stamp_id=stamp_id,
        pair_id=pair_id,
        order_book=order_book,
    )
    session.add(order_book)
    return order_book


async def find_all_between(
    session: AsyncSession,
    begin_time: DateTime,
    end_time: DateTime,
    pair_id: UUID,
) -> list[OrderBookModel]:
    # Condition for specific pair_id and time interval
    condition = text(
        "pair_id = :pair_id AND created_at BETWEEN :begin_time AND :end_time"
    ).bindparams(pair_id=pair_id, begin_time=begin_time, end_time=end_time)

    # Select raw data ordering it by pair id and creation time
    stmt = (
        select(OrderBookModel)
        .where(condition)
        .order_by(asc(OrderBookModel.created_at))
    )

    # Return result of statement
    result = await session.execute(stmt)

    return result.scalars().all()
