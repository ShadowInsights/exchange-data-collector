import logging

from app.services.collectors.workers.db_worker import Worker, set_interval


class WallsWorker(Worker):

    @set_interval(1)
    async def run(self):
        logging.info("TEST")
