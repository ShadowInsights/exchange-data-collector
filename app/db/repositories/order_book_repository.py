from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order_book import OrderBookModel


async def crate_order_book(
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
