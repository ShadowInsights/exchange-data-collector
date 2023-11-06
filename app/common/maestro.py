import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from app.common.config import settings
from app.common.database import get_async_db
from app.db.models.pair import PairModel
from app.db.repositories.maestro_repository import (
    create_maestro, update_maestro_liveness_time)
from app.db.repositories.pair_repository import (
    find_all_not_collecting_pairs_for_update, update_pairs_maestro_id)
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector
from app.services.starters.liquidity_starters import \
    fill_missed_liquidity_intervals
from app.utils.scheduling_utils import set_interval


class Maestro:
    def __init__(self, launch_id: UUID) -> None:
        self._launch_id = launch_id
        self._binance_collectors_tasks: list[asyncio.Task] = []

    async def run(self) -> None:
        maestro_id = await self._create_maestro()
        asyncio.create_task(self._liveness_updater_loop(maestro_id))
        pairs = await self._retrieve_and_assign_pairs(maestro_id)
        await self._start_collectors(maestro_id, pairs)

    @set_interval(settings.MAESTRO_LIVENESS_UPDATER_JOB_INTERVAL)
    async def _liveness_updater_loop(self, maestro_id: UUID, *args, **kwargs) -> None:
        async with get_async_db() as db:
            await update_maestro_liveness_time(db, maestro_id)
        callback_event = kwargs.get('callback_event')
        callback_event.set()

    async def _create_maestro(self) -> UUID:
        async with get_async_db() as db:
            maestro_model = await create_maestro(db, self._launch_id)
        logging.info(f"Maestro created {maestro_model.id}")
        return maestro_model.id

    async def _retrieve_and_assign_pairs(
            self, maestro_id: UUID
    ) -> list[PairModel]:
        while True:
            try:
                await asyncio.sleep(settings.MAESTRO_PAIRS_RETRIEVAL_INTERVAL)
                logging.info("Retrieving pairs for data collection")
                liveness_time_interval = datetime.now() - timedelta(minutes=1)
                async with get_async_db() as db:
                    pairs = await find_all_not_collecting_pairs_for_update(
                        db, liveness_time_interval
                    )
                    if pairs:
                        await update_pairs_maestro_id(db, pairs, maestro_id)
                        logging.info("Pairs retrieved")
                        return pairs
                    else:
                        logging.info("No pairs found")
            except Exception as e:
                logging.exception(f"Error while retrieving pairs: {e}")

    async def _start_collectors(
            self, maestro_id: UUID, pairs: list[PairModel]
    ) -> None:
        logging.info("Filling missed liquidity intervals")
        await fill_missed_liquidity_intervals(maestro_id)

        logging.info("Starting data collection")
        logging.info(f"Launch ID: {self._launch_id}")

        for pair in pairs:
            collector = BinanceExchangeCollector(
                launch_id=self._launch_id,
                pair_id=pair.id,
                exchange_id=pair.exchange_id,
                symbol=pair.symbol,
                delimiter=pair.delimiter,
            )
            self._binance_collectors_tasks.append(collector.run())

        await asyncio.gather(*self._binance_collectors_tasks)
