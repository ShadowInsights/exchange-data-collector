from typing import List

from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models.order_book import OrderBookModel


async def save_order_book(
    self,
    db: AsyncSession,
) -> OrderBookModel:
    pass
