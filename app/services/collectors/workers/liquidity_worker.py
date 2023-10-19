import asyncio
import copy
import logging
import math

from app.common.config import settings
from app.common.database import get_async_db, get_sync_db
from app.db.repositories.liquidity_repository import (
    find_sync_last_n_liquidity, save_liquidity)
from app.services.collectors.common import Collector
from app.services.collectors.workers.common import Worker
from app.services.collectors.workers.db_worker import set_interval
from app.services.messengers.liquidity_discord_messenger import \
    LiquidityDiscordMessenger
from app.utils.math_utils import calculate_round_avg


class LiquidityWorker(Worker):
    def __init__(
        self,
        collector: Collector,
        discord_messenger: LiquidityDiscordMessenger,
        comparable_liquidity_set_size: int = settings.COMPARABLE_LIQUIDITY_SET_SIZE,
        liquidity_anomaly_ratio: float = settings.LIQUIDITY_ANOMALY_RATIO,
    ):
        self._collector = collector
        self._discord_messenger = discord_messenger
        self._comparable_liquidity_set_size = comparable_liquidity_set_size
        self._liquidity_anomaly_ratio = liquidity_anomaly_ratio
        self._last_avg_volumes = self._find_last_average_volumes()

    @set_interval(settings.LIQUIDITY_WORKER_JOB_INTERVAL)
    async def run(self) -> None:
        await super().run()

    async def _run_worker(self) -> None:
        logging.debug("Saving liquidity record")

        average_volume = copy.deepcopy(self._collector.avg_volume)

        # Save liquidity record
        await self._save_liquidity_record(average_volume)

        # Perform anomaly analysis
        await self._perform_anomaly_analysis(average_volume)

    async def _save_liquidity_record(self, avg_volume: float) -> None:
        async with (get_async_db() as session):
            # Save  runtime liquidity record
            await save_liquidity(
                session,
                avg_volume=avg_volume,
                launch_id=self._collector.launch_id,
                pair_id=self._collector.pair_id,
            )

    async def _perform_anomaly_analysis(self, average_volume: float) -> None:
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

            # Send alert notification via standard messenger implementation
            asyncio.create_task(
                self._discord_messenger.send_notification(
                    pair_id=self._collector.pair_id,
                    deviation=deviation,
                    current_avg_volume=round(average_volume),
                    previous_avg_volume=calculate_round_avg(
                        self._last_avg_volumes,
                        self._comparable_liquidity_set_size,
                    ),
                )
            )

        # Update avg volumes queue with last avg volume
        self._last_avg_volumes.pop(0)
        self._last_avg_volumes.append(average_volume)

        # Clean volume stats for elapsed time period
        self._collector.clear_volume_stats()

    def _find_last_average_volumes(self) -> list:
        with get_sync_db() as session:
            # Get last n liquidity records by pair id
            last_liquidity_records = find_sync_last_n_liquidity(
                session,
                self._collector.pair_id,
                self._comparable_liquidity_set_size,
            )

            # Fill last avg volumes with average volume from extracted liquidity records
            return [
                liquidity.average_volume
                for liquidity in last_liquidity_records
            ]

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
