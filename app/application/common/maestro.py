import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from _decimal import Decimal

from app.application.collectors.binance_collector import BinanceCollector
from app.application.collectors.coinbase_collector import CoinbaseCollector
from app.application.collectors.kraken_collector import KrakenCollector
from app.application.common.collector import Collector
from app.application.common.processor import Processor
from app.application.messengers.discord.order_book_discord_messenger import \
    OrderBookDiscordMessenger
from app.application.messengers.discord.orders_anomalies_summary_discord_messenger import \
    OrdersAnomaliesSummaryDiscordMessenger
from app.application.messengers.discord.volume_discord_messenger import \
    VolumeDiscordMessenger
from app.application.messengers.telegram.order_book_telegram_messenger import \
    OrderBookTelegramMessenger
from app.application.messengers.telegram.orders_anomalies_summary_telegram_messenger import \
    OrdersAnomaliesSummaryTelegramMessenger
from app.application.messengers.telegram.volume_telegram_messenger import \
    VolumeTelegramMessenger
from app.application.workers.common import Worker
from app.application.workers.db_worker import DbWorker
from app.application.workers.orders_anomalies_summary_worker import \
    OrdersAnomaliesSummaryWorker
from app.application.workers.orders_worker import OrdersWorker
from app.application.workers.volume_worker import VolumeWorker
from app.config import settings
from app.infrastructure.db.database import get_async_db
from app.infrastructure.db.models.exchange import LiteralExchangeName
from app.infrastructure.db.repositories.exchange_repository import \
    find_exchange_by_id
from app.infrastructure.db.repositories.maestro_repository import (
    CollectingPairsForUpdateResult, create_maestro,
    create_maestro_pair_associations, delete_maestro_by_id,
    find_all_not_collecting_pairs_for_update, update_maestro_liveness_time,
    update_maestro_pair_associations)
from app.infrastructure.db.repositories.pair_repository import find_pair_by_id
from app.utilities.event_utils import EventHandler
from app.utilities.scheduling_utils import SetInterval


class Maestro:
    def __init__(
        self,
        launch_id: UUID,
        maestro_pairs_retrieval_interval: float = settings.MAESTRO_PAIRS_RETRIEVAL_INTERVAL,
        maestro_max_liveness_gap_minutes: int = settings.MAESTRO_MAX_LIVENESS_GAP_SECONDS,
    ) -> None:
        self._launch_id = launch_id
        self._maestro_pairs_retrieval_interval = (
            maestro_pairs_retrieval_interval
        )
        self._maestro_max_liveness_gap_minutes = (
            maestro_max_liveness_gap_minutes
        )
        self._processor_tasks: list[asyncio.Task] = []

    async def run(self) -> None:
        await self._init_maestro()
        asyncio.create_task(self._liveness_updater_loop())
        pairs = await self._retrieve_and_assign_pairs()
        await self._start_processors(pairs)

    @SetInterval(
        settings.MAESTRO_LIVENESS_UPDATER_JOB_INTERVAL,
        name="Maestro liveness updater",
    )
    async def _liveness_updater_loop(
        self, callback_event: asyncio.Event | None = None
    ) -> None:
        async with get_async_db() as db:
            await update_maestro_liveness_time(db, self._maestro_id)
        if callback_event:
            callback_event.set()

    async def _init_maestro(self) -> None:
        async with get_async_db() as db:
            maestro_model = await create_maestro(db, self._launch_id)

        self._maestro_id = UUID(str(maestro_model.id))

        logging.info(f"Maestro initialized with id={self._maestro_id}")

    async def _retrieve_and_assign_pairs(
        self,
    ) -> list[UUID]:
        logging.info("Retrieving pairs for data collection")

        while True:
            try:
                await asyncio.sleep(self._maestro_pairs_retrieval_interval)

                async with get_async_db() as db:
                    result = await find_all_not_collecting_pairs_for_update(
                        db,
                        datetime.utcnow()
                        - timedelta(
                            seconds=self._maestro_max_liveness_gap_minutes
                        ),
                    )
                    if len(result.pair_ids) == 0:
                        continue
                    if isinstance(result, CollectingPairsForUpdateResult):
                        await update_maestro_pair_associations(
                            db,
                            result.attached_maestro_id,
                            self._maestro_id,
                            False,
                        )
                        await delete_maestro_by_id(
                            db, result.attached_maestro_id
                        )
                        logging.info("Pairs reassignment completed")
                    else:
                        await create_maestro_pair_associations(
                            db, self._maestro_id, result.pair_ids
                        )
                        logging.info("Pairs assignment completed")
                    logging.info(f"Pairs retrieved: {result.pair_ids}")
                    return result.pair_ids
            except Exception as e:
                logging.exception(f"Error while retrieving pairs: {e}")

    async def _start_processors(self, pair_ids: list[UUID]) -> None:
        logging.info("Starting data collection")
        logging.info(f"Launch ID: {self._launch_id}")

        for pair_id in pair_ids:
            event_handler = EventHandler()

            async with get_async_db() as session:
                pair = await find_pair_by_id(session, pair_id)
                exchange = await find_exchange_by_id(session, pair.exchange_id)

            # Create collector for necessary exchange
            collector = self._create_collector(
                exchange_name=exchange.name,
                launch_id=self._launch_id,
                pair_id=UUID(str(pair.id)),
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
                pair_id=UUID(str(pair.id)),
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
    ) -> None:
        default_workers: list[Worker] = [
            DbWorker(processor=processor),
            VolumeWorker(
                processor=processor,
                event_handler=event_handler,
                messengers=[
                    VolumeDiscordMessenger(),
                    VolumeTelegramMessenger(),
                ],
            ),
            OrdersWorker(
                processor=processor,
                messengers=[
                    OrderBookDiscordMessenger(),
                    OrderBookTelegramMessenger(),
                ],
            ),
            OrdersAnomaliesSummaryWorker(
                processor=processor,
                messengers=[
                    OrdersAnomaliesSummaryDiscordMessenger(),
                    OrdersAnomaliesSummaryTelegramMessenger(),
                ],
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
            case "COINBASE":
                return CoinbaseCollector(
                    launch_id=launch_id,
                    pair_id=pair_id,
                    symbol=symbol,
                    delimiter=delimiter,
                )
            case _:
                raise Exception(f"Exchange {exchange_name} is not supported")
