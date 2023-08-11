from typing import List

from app.db.database import ClickHousePool
from app.db.models.binance_order import BinanceOrderModel

# from app.main import ch_connection_pool as pool


class ClickHouseRepository:
    def __init__(self, pool: ClickHousePool):
        self._pool = pool

    async def save_bucket(self, orders: List[BinanceOrderModel]):
        data = [order.to_dict() for order in orders]

        query = """
        INSERT INTO binance_orderbook (id, launch_id, order_type, price,
          quantity, bucket_id, pair_id, exchange_id, stamp_id, created_at) 
        VALUES
        """

        await self._pool.execute(query, data)
