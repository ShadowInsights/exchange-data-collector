import asyncio
import concurrent.futures
import copy
import logging

from _decimal import Decimal

from app.common.config import settings
from app.common.database import get_async_db, get_sync_db
from app.common.processor import Processor
from app.db.repositories.volume_repository import (find_sync_last_n_volumes,
                                                   save_volume)
from app.services.collectors.clients.schemas.common import EventTypeEnum
from app.services.messengers.volume_discord_messenger import \
    VolumeDiscordMessenger
from app.services.workers.common import Worker
from app.utils.event_utils import EventHandler
from app.utils.math_utils import calculate_avg_by_summary, calculate_round_avg
from app.utils.scheduling_utils import SetInterval


class VolumeWorker(Worker):
    def __init__(
        self,
        processor: Processor,
        discord_messenger: VolumeDiscordMessenger,
        event_handler: EventHandler,
        volume_anomaly_ratio: Decimal = settings.VOLUME_ANOMALY_RATIO,
        volume_comparative_array_size: int = settings.VOLUME_COMPARATIVE_ARRAY_SIZE,
        executor_factory: concurrent.futures.Executor = None,
    ):
        super().__init__(processor=processor)
        self._event_handler = event_handler
        self._discord_messenger = discord_messenger
        self._executor_factory = (
            executor_factory or concurrent.futures.ThreadPoolExecutor
        )
        self._volume_anomaly_ratio = Decimal(volume_anomaly_ratio)
        self._volume_comparative_array_size = volume_comparative_array_size
        self._last_average_volumes = self._find_last_average_volumes()
        self._summary_volume_per_interval = 0
        self._volume_updates_counter_per_interval = 0
        self._event_handler.on(
            EventTypeEnum.UPDATE.value, self.__update_summary_volume
        )

    @SetInterval(settings.VOLUME_WORKER_JOB_INTERVAL)
    async def run(self, callback_event: asyncio.Event = None) -> None:
        await super().run(callback_event)

    async def _run_worker(self, callback_event: asyncio.Event = None) -> None:
        logging.debug("Saving liquidity record")

        last_avg_volumes = copy.deepcopy(self._last_average_volumes)

        average_volume = calculate_avg_by_summary(
            summary=self._summary_volume_per_interval,
            counter=self._volume_updates_counter_per_interval,
        )

        # Save liquidity record
        await self._save_liquidity_record(average_volume)

        # Perform anomaly analysis
        with self._executor_factory() as executor:
            deviation = await asyncio.get_event_loop().run_in_executor(
                executor, self.__perform_anomaly_analysis, average_volume
            )

        # Send alert notification if deviation is critical
        if deviation:
            self.__send_notification(
                deviation=deviation,
                average_volume=average_volume,
                last_average_volumes=last_avg_volumes,
            )

    def __perform_anomaly_analysis(
        self, average_volume: Decimal
    ) -> Decimal | None:
        result = None

        # if comparable liquidity set size is not optimal, then just add saved liquidity record to set
        if (
            len(self._last_average_volumes)
            != self._volume_comparative_array_size
        ):
            self._last_average_volumes.append(average_volume)

            # Clean volume stats for elapsed time period
            self.__clear_volume_stats()

            return

        # Check avg volume for anomaly based on last n avg volumes
        deviation = self.__calculate_deviation(average_volume)

        if deviation >= self._volume_anomaly_ratio or deviation <= (
            1 / self._volume_anomaly_ratio
        ):
            logging.info(
                "Found anomaly inflow of volume. Sending alert notification..."
            )
            result = deviation

        # Update avg volumes queue with last avg volume
        self._last_average_volumes.pop(0)
        self._last_average_volumes.append(average_volume)

        # Clean volume stats for elapsed time period
        self.__clear_volume_stats()

        return result

    def __send_notification(
        self,
        deviation: Decimal,
        average_volume: int,
        last_average_volumes: list[int],
    ) -> None:
        asyncio.create_task(
            self._discord_messenger.send_notification(
                pair_id=self._processor.pair_id,
                deviation=deviation,
                current_avg_volume=round(average_volume),
                previous_avg_volume=calculate_round_avg(
                    last_average_volumes,
                    self._volume_comparative_array_size,
                ),
            )
        )

    async def _save_liquidity_record(self, avg_volume: int) -> None:
        async with get_async_db() as session:
            # Save  runtime liquidity record
            await save_volume(
                session,
                avg_volume=avg_volume,
                launch_id=self._processor.launch_id,
                pair_id=self._processor.pair_id,
            )

    def _find_last_average_volumes(self) -> list:
        with get_sync_db() as session:
            # Get last n liquidity records by pair id
            last_average_volumes = find_sync_last_n_volumes(
                session,
                self._processor.pair_id,
                self._volume_comparative_array_size,
            )

            session.expunge_all()

        # Fill last avg volumes with average volume from extracted liquidity records
        return [liquidity.average_volume for liquidity in last_average_volumes]

    def __calculate_deviation(self, average_volume: Decimal) -> Decimal:
        # Calculate avg volume based on n last volumes
        common_avg_volume = calculate_round_avg(
            value_arr=self._last_average_volumes,
            counter=self._volume_comparative_array_size,
        )

        # Calculate deviation for avg volume of current time interval in comparison to last n volumes
        deviation = average_volume / common_avg_volume
        logging.debug(
            f"Deviation for {average_volume} volume in comparison "
            f"to common {common_avg_volume} volume - {deviation}"
        )

        return deviation

    def __update_summary_volume(self) -> None:
        logging.debug("Updating average volume")

        self._volume_updates_counter_per_interval += 1

        # Concat bids with asks and calculate total volume of order_book
        for price, quantity in {
            **self._processor.order_book.a,
            **self._processor.order_book.b,
        }.items():
            self._summary_volume_per_interval += price * quantity

    def __clear_volume_stats(self):
        logging.debug("Cleaning volume stats")

        self._summary_volume_per_interval = 0
        self._volume_updates_counter_per_interval = 0
