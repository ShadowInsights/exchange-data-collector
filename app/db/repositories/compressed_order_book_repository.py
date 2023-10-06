from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.compressed_order_book import CompressedOrderBook


async def save_all_compressed_order_book(
    session: AsyncSession, reports: list[CompressedOrderBook]
):
    for report in reports:
        session.add(report)
