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
