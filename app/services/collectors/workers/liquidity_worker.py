import asyncio
import logging

from app.common.config import settings
from app.common.database import get_async_db, get_sync_db
from app.db.repositories.liquidity_repository import (
    find_sync_last_n_liquidity, save_liquidity)
from app.services.collectors.common import Collector
from app.services.collectors.workers.common import Worker
from app.services.collectors.workers.db_worker import set_interval
from app.services.messengers.liquidity_discord_messenger import \
    LiquidityDiscordMessenger
from app.utils.math_utils import calc_round_avg


class LiquidityWorker(Worker):

    def find_last_average_volumes(self) -> list:
        with get_sync_db() as session:
            # Get last n liquidity records by pair id
            last_liquidity_records = find_sync_last_n_liquidity(
                session,
                self._collector.pair_id,
                settings.COMPARABLE_LIQUIDITY_SET_SIZE,
            )

            # Fill last avg volumes with average volume from extracted liquidity records
            return [
                liquidity.average_volume
                for liquidity in last_liquidity_records
            ]

    def __init__(
            self,
            collector: Collector,
            discord_messenger: LiquidityDiscordMessenger,
    ):
        self._collector = collector
        self._discord_messenger = discord_messenger

        self._last_avg_volumes = self.find_last_average_volumes()

    @set_interval(settings.LIQUIDITY_WORKER_JOB_INTERVAL)
    async def run(self) -> None:
        await super().run()

    async def _run_worker(self) -> None:
        logging.debug("Saving liquidity record")

        async with (get_async_db() as session):
            # Save  runtime liquidity record
            await save_liquidity(
                session,
                avg_volume=self._collector.avg_volume,
                launch_id=self._collector.launch_id,
                pair_id=self._collector.pair_id,
            )

        # Perform anomaly analysis
        await self.__perform_anomaly_analysis()

    async def __perform_anomaly_analysis(self) -> None:
        # if comparable liquidity set size is not optimal, then just add saved liquidity record to set
        if (
                len(self._last_avg_volumes)
                != settings.COMPARABLE_LIQUIDITY_SET_SIZE
        ):
            self._last_avg_volumes.append(self._collector.avg_volume)

            # Clean volume stats for elapsed time period
            self._collector.clear_volume_stats()

            return

        # Check avg volume for anomaly based on last n avg volumes
        deviation = self.__calculate_deviation()

        if deviation > settings.LIQUIDITY_ANOMALY_RATIO or deviation < (
                1 / settings.LIQUIDITY_ANOMALY_RATIO
        ):
            logging.info(
                "Found anomaly inflow of volume. Sending alert notification..."
            )

            # Send alert notification via standard messenger implementation
            asyncio.create_task(
                self._discord_messenger.send_notification(
                    pair_id=self._collector.pair_id,
                    deviation=deviation,
                    current_avg_volume=self._collector.avg_volume,
                    previous_avg_volume=calc_round_avg(
                        self._last_avg_volumes,
                        settings.COMPARABLE_LIQUIDITY_SET_SIZE,
                    ),
                )
            )

        # Update avg volumes queue with last avg volume
        self._last_avg_volumes.pop(0)
        self._last_avg_volumes.append(self._collector.avg_volume)

        # Clean volume stats for elapsed time period
        self._collector.clear_volume_stats()

    def __calculate_deviation(self) -> float:
        # Calculate avg volume based on n last volumes
        common_avg_volume = round(
            calc_round_avg(
                value_arr=self._last_avg_volumes,
                counter=settings.COMPARABLE_LIQUIDITY_SET_SIZE,
            )
        )

        # Calculate deviation for avg volume of current time interval in comparison to last n volumes
        deviation = self._collector.avg_volume / common_avg_volume
        logging.debug(
            f"Deviation for {self._collector.avg_volume} volume in comparison "
            f"to common {common_avg_volume} volume - {deviation}"
        )

        return deviation
