import logging

from app.services.collectors.workers.db_worker import Worker, set_interval


class LiquidityWorker(Worker):
    def __init__(self, collector):
        self._collector = collector

    @set_interval(15)
    async def run(self):
        logging.info("Liquidity worker")
