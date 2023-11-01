from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order_book_anomaly import OrderBookAnomalyModel


async def create_order_book_anomalies(
    session: AsyncSession,
    order_book_anomalies: list[OrderBookAnomalyModel],
) -> list[OrderBookAnomalyModel]:
    session.add_all(order_book_anomalies)
    return order_book_anomalies
