import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from _decimal import Decimal

from app.common.config import settings
from app.common.database import get_async_db
from app.common.processor import Processor
from app.db.models.exchange import LiteralExchangeName
from app.db.models.pair import PairModel
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.maestro_repository import (
    create_maestro, update_maestro_liveness_time)
from app.db.repositories.pair_repository import (
    find_all_not_collecting_pairs_for_update, update_pairs_maestro_id)
from app.services.collectors.binance_collector import BinanceCollector
from app.services.collectors.common import Collector
from app.services.collectors.kraken_collector import KrakenCollector
from app.services.messengers.order_book_discord_messenger import \
    OrderBookDiscordMessenger
from app.services.messengers.volume_discord_messenger import \
    VolumeDiscordMessenger
# from app.services.starters.volume_starters import fill_missed_volume_intervals
from app.services.workers.db_worker import DbWorker
from app.services.workers.orders_worker import OrdersWorker
from app.services.workers.volume_worker import VolumeWorker
from app.utils.event_utils import EventHandler
from app.utils.scheduling_utils import SetInterval


class Maestro:
    def __init__(self, launch_id: UUID) -> None:
        self._launch_id = launch_id
        self._processor_tasks: list[asyncio.Task] = []

    async def run(self) -> None:
        maestro_id = await self._create_maestro()
        asyncio.create_task(self._liveness_updater_loop(maestro_id))
        pairs = await self._retrieve_and_assign_pairs(maestro_id)
        await self._start_processors(maestro_id, pairs)

    @SetInterval(settings.MAESTRO_LIVENESS_UPDATER_JOB_INTERVAL)
    async def _liveness_updater_loop(
        self, maestro_id: UUID, callback_event: asyncio.Event = None
    ) -> None:
        async with get_async_db() as db:
            await update_maestro_liveness_time(db, maestro_id)
        if callback_event:
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

    async def _start_processors(
        self, maestro_id: UUID, pairs: list[PairModel]
    ) -> None:
        # TODO: Remake filling missed volumes
        # logging.info("Filling missed liquidity intervals")
        # await fill_missed_volume_intervals(maestro_id)

        logging.info("Starting data collection")
        logging.info(f"Launch ID: {self._launch_id}")

        for pair in pairs:
            event_handler = EventHandler()

            async with get_async_db() as session:
                exchange = await find_exchange_by_id(session, pair.exchange_id)
                exchange_name = exchange.name

            # Create collector for necessary exchange
            collector = self._create_collector(
                exchange_name=exchange_name,
                launch_id=self._launch_id,
                pair_id=pair.id,
                symbol=pair.symbol,
                delimiter=pair.delimiter,
            )

            # Create associated processor for collector
            processor = Processor(
                launch_id=self._launch_id,
                event_handler=event_handler,
                collector=collector,
                symbol=pair.symbol,
                delimiter=pair.delimiter,
                pair_id=pair.id,
            )

            task = asyncio.create_task(processor.run())

            # TODO Launch workers only after snapshot of collector
            self._create_default_workers(
                processor=processor, event_handler=event_handler
            )

            self._processor_tasks.append(task)

        await asyncio.gather(*self._processor_tasks)

    def _create_default_workers(
        self, processor: Processor, event_handler: EventHandler
    ):
        default_workers = [
            DbWorker(processor=processor),
            VolumeWorker(
                processor=processor,
                event_handler=event_handler,
                discord_messenger=VolumeDiscordMessenger(),
            ),
            OrdersWorker(
                processor=processor,
                discord_messenger=OrderBookDiscordMessenger(),
            ),
        ]

        for worker in default_workers:
            asyncio.create_task(worker.run())

    def _create_collector(
        self,
        exchange_name: LiteralExchangeName,
        launch_id: UUID,
        pair_id: UUID,
        symbol: str,
        delimiter: Decimal,
    ) -> Collector:
        match exchange_name:
            case "BINANCE":
                return BinanceCollector(
                    launch_id=launch_id,
                    pair_id=pair_id,
                    symbol=symbol,
                    delimiter=delimiter,
                )
            case "KRAKEN":
                return KrakenCollector(
                    launch_id=launch_id,
                    pair_id=pair_id,
                    symbol=symbol,
                    delimiter=delimiter,
                )
            case _:
                raise Exception(f"Exchange {exchange_name} is not supported")
