from typing import List
import asyncio
from clickhouse_driver import Client
from app.db.models.binance_order import BinanceOrderModel


class ClickHouseRepository:
    def __init__(self, ch_client: Client):
        self.ch_client = ch_client

    async def save_bucket(self, orders: List[BinanceOrderModel]):
        data = [order.to_dict() for order in orders]

        query = """
        INSERT INTO binance_orderbook (id, launch_id, order_type, price, quantity, bucket_id, pair_id, exchange_id, stamp_id, created_at) 
        VALUES
        """

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.ch_client.execute, query, data)
