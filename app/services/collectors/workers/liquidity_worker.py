import asyncio
import concurrent.futures
import copy
import logging

from app.common.config import settings
from app.common.database import get_async_db, get_sync_db
from app.db.repositories.liquidity_repository import (
    find_sync_last_n_liquidity, save_liquidity)
from app.services.collectors.common import Collector
from app.services.collectors.workers.common import Worker
from app.services.messengers.liquidity_discord_messenger import \
    LiquidityDiscordMessenger
from app.utils.math_utils import calculate_round_avg
from app.utils.scheduling_utils import SetInterval


class LiquidityWorker(Worker):
    def __init__(
        self,
        collector: Collector,
        discord_messenger: LiquidityDiscordMessenger,
        comparable_liquidity_set_size: int = settings.COMPARABLE_LIQUIDITY_SET_SIZE,
        liquidity_anomaly_ratio: float = settings.LIQUIDITY_ANOMALY_RATIO,
        executor_factory: concurrent.futures.Executor = None,
    ):
        self._collector = collector
        self._discord_messenger = discord_messenger
        self._comparable_liquidity_set_size = comparable_liquidity_set_size
        self._liquidity_anomaly_ratio = liquidity_anomaly_ratio
        self._last_avg_volumes = self._find_last_average_volumes()
        # TODO: add support for different executor types
        self._executor_factory = (
            executor_factory or concurrent.futures.ThreadPoolExecutor
        )

    @SetInterval(settings.LIQUIDITY_WORKER_JOB_INTERVAL)
    async def run(self, callback_event: asyncio.Event = None) -> None:
        await super().run(callback_event)
        if callback_event:
            callback_event.set()

    async def _run_worker(self, callback_event: asyncio.Event = None) -> None:
        logging.debug("Saving liquidity record")

        average_volume = copy.deepcopy(self._collector.avg_volume)
        last_avg_volume = copy.deepcopy(self._last_avg_volumes)

        # Save liquidity record
        await self._save_liquidity_record(average_volume)

        # Perform anomaly analysis
        with self._executor_factory() as executor:
            deviation = await asyncio.get_event_loop().run_in_executor(
                executor, self._perform_anomaly_analysis, average_volume
            )

        # Send alert notification via standard messenger implementation
        if deviation:
            asyncio.create_task(
                self._discord_messenger.send_notification(
                    pair_id=self._collector.pair_id,
                    deviation=deviation,
                    current_avg_volume=round(average_volume),
                    previous_avg_volume=calculate_round_avg(
                        last_avg_volume,
                        self._comparable_liquidity_set_size,
                    ),
                )
            )

    async def _save_liquidity_record(self, avg_volume: float) -> None:
        async with get_async_db() as session:
            # Save  runtime liquidity record
            await save_liquidity(
                session,
                avg_volume=avg_volume,
                launch_id=self._collector.launch_id,
                pair_id=self._collector.pair_id,
            )

    def _perform_anomaly_analysis(self, average_volume: float) -> float | None:
        result = None

        # if comparable liquidity set size is not optimal, then just add saved liquidity record to set
        if len(self._last_avg_volumes) != self._comparable_liquidity_set_size:
            self._last_avg_volumes.append(average_volume)

            # Clean volume stats for elapsed time period
            self._collector.clear_volume_stats()

            return

        # Check avg volume for anomaly based on last n avg volumes
        deviation = self.__calculate_deviation(average_volume)

        if deviation >= self._liquidity_anomaly_ratio or deviation <= (
            1 / self._liquidity_anomaly_ratio
        ):
            logging.info(
                "Found anomaly inflow of volume. Sending alert notification..."
            )
            result = deviation

        # Update avg volumes queue with last avg volume
        self._last_avg_volumes.pop(0)
        self._last_avg_volumes.append(average_volume)

        # Clean volume stats for elapsed time period
        self._collector.clear_volume_stats()

        return result

    def _find_last_average_volumes(self) -> list:
        with get_sync_db() as session:
            # Get last n liquidity records by pair id
            last_average_volumes = find_sync_last_n_liquidity(
                session,
                self._collector.pair_id,
                self._comparable_liquidity_set_size,
            )

            session.expunge_all()

        # Fill last avg volumes with average volume from extracted liquidity records
        return [liquidity.average_volume for liquidity in last_average_volumes]

    def __calculate_deviation(self, average_volume: float) -> float:
        # Calculate avg volume based on n last volumes
        common_avg_volume = round(
            calculate_round_avg(
                value_arr=self._last_avg_volumes,
                counter=self._comparable_liquidity_set_size,
            )
        )

        # Calculate deviation for avg volume of current time interval in comparison to last n volumes
        deviation = average_volume / common_avg_volume
        logging.debug(
            f"Deviation for {average_volume} volume in comparison "
            f"to common {common_avg_volume} volume - {deviation}"
        )

        return deviation
