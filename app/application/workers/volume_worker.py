import asyncio
import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import Executor

from _decimal import Decimal

from app.application.common.processor import Processor
from app.application.messengers.volume_messenger import (
    VolumeMessenger,
    VolumeNotification,
)
from app.application.workers.common import Worker
from app.config import settings
from app.infrastructure.clients.schemas.common import EventTypeEnum
from app.infrastructure.db.database import get_async_db, get_sync_db
from app.infrastructure.db.repositories.volume_repository import (
    find_sync_last_n_volumes,
    save_volume,
)
from app.utilities.event_utils import EventHandler
from app.utilities.math_utils import (
    calculate_avg_by_summary,
    calculate_decimal_average,
    calculate_diff_over_sum,
    calculate_int_average,
    round_to_int,
)
from app.utilities.scheduling_utils import SetInterval


class VolumeWorker(Worker):
    def __init__(
        self,
        processor: Processor,
        event_handler: EventHandler,
        messengers: list[VolumeMessenger] = [],
        executor_factory: type[Executor] = ThreadPoolExecutor,
        volume_anomaly_ratio: Decimal = Decimal(settings.VOLUME_ANOMALY_RATIO),
        volume_comparative_array_size: int = settings.VOLUME_COMPARATIVE_ARRAY_SIZE,
    ):
        super().__init__(processor=processor)
        self._event_handler = event_handler
        self._messengers = messengers
        # TODO: add support for different executor types
        self._executor_factory = executor_factory
        self._volume_anomaly_ratio = Decimal(volume_anomaly_ratio)
        self._volume_comparative_array_size = volume_comparative_array_size
        self._last_average_volumes = self._find_last_average_volumes()
        self._last_bid_ask_ratio: list[float] = self._find_last_bid_ask_ratio()
        self._summary_asks_volume_per_interval: int = 0
        self._summary_bids_volume_per_interval: int = 0
        self._summary_volume_per_interval: int = 0
        self._volume_updates_counter_per_interval: int = 0
        self._event_handler.on(
            EventTypeEnum.UPDATE.value, self.__update_summary_volume
        )

    @SetInterval(settings.VOLUME_WORKER_JOB_INTERVAL, name="Volume worker")
    async def run(self, callback_event: asyncio.Event | None = None) -> None:
        await super().run(callback_event)
        if callback_event:
            callback_event.set()

    async def _run_worker(self, _: asyncio.Event | None = None) -> None:
        logging.debug(
            f"Volume processing cycle started [symbol={self._processor.symbol}]"
        )

        last_bid_ask_ratio = copy.deepcopy(self._last_bid_ask_ratio)
        last_avg_volumes = copy.deepcopy(self._last_average_volumes)

        average_bids_volume = calculate_avg_by_summary(
            summary=self._summary_bids_volume_per_interval,
            counter=self._volume_updates_counter_per_interval,
        )

        average_asks_volume = calculate_avg_by_summary(
            summary=self._summary_asks_volume_per_interval,
            counter=self._volume_updates_counter_per_interval,
        )

        bid_ask_ratio = calculate_diff_over_sum(
            diminished=average_bids_volume, subtrahend=average_asks_volume
        )

        average_volume = calculate_avg_by_summary(
            summary=self._summary_volume_per_interval,
            counter=self._volume_updates_counter_per_interval,
        )

        # Save liquidity record
        await self._save_liquidity_record(average_volume, bid_ask_ratio)

        # Perform anomaly analysis
        with self._executor_factory() as executor:
            deviation = await asyncio.get_event_loop().run_in_executor(
                executor, self.__perform_anomaly_analysis, average_volume
            )

        # Send alert notification if deviation is critical
        if deviation:
            await self._send_notification(
                deviation=deviation,
                bid_ask_ratio=Decimal(bid_ask_ratio),
                previous_bid_ask_ratio=calculate_decimal_average(
                    last_bid_ask_ratio, self._volume_comparative_array_size
                ),
                average_volume=average_volume,
                previous_average_volume=calculate_int_average(
                    last_avg_volumes,
                    self._volume_comparative_array_size,
                ),
            )

        logging.debug(
            f"Volume processing cycle finished [symbol={self._processor.symbol}]"
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

            return None

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

    async def _send_notification(
        self,
        deviation: Decimal,
        bid_ask_ratio: Decimal,
        previous_bid_ask_ratio: Decimal,
        average_volume: int,
        previous_average_volume: int,
    ) -> None:
        tasks = []

        notification = VolumeNotification(
            pair_id=self._processor.pair_id,
            deviation=deviation,
            current_bid_ask_ratio=bid_ask_ratio,
            previous_bid_ask_ratio=previous_bid_ask_ratio,
            current_avg_volume=average_volume,
            previous_avg_volume=previous_average_volume,
        )

        for messenger in self._messengers:
            tasks.append(
                asyncio.create_task(
                    messenger.send_notification(notification=notification)
                )
            )

        await asyncio.gather(*tasks)

    async def _save_liquidity_record(
        self, avg_volume: int, bid_ask_ratio: Decimal
    ) -> None:
        async with get_async_db() as session:
            # Save  runtime liquidity record
            await save_volume(
                session,
                bid_ask_ratio=bid_ask_ratio,
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

    def _find_last_bid_ask_ratio(self) -> list:
        with get_sync_db() as session:
            # Get last n liquidity records by pair id
            last_bid_ask_ratio = find_sync_last_n_volumes(
                session,
                self._processor.pair_id,
                self._volume_comparative_array_size,
            )

            session.expunge_all()

        return [liquidity.bid_ask_ratio for liquidity in last_bid_ask_ratio]

    def __calculate_deviation(self, average_volume: Decimal) -> Decimal:
        # Calculate avg volume based on n last volumes
        common_avg_volume = calculate_int_average(
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

        for price, quantity in {**self._processor.order_book.b}.items():
            self._summary_bids_volume_per_interval += round_to_int(
                price * quantity
            )

        for price, quantity in {**self._processor.order_book.a}.items():
            self._summary_asks_volume_per_interval += round_to_int(
                price * quantity
            )

        # Concat bids with asks and calculate total volume of order_book
        self._summary_volume_per_interval = (
            self._summary_bids_volume_per_interval
            + self._summary_asks_volume_per_interval
        )

    def __clear_volume_stats(self) -> None:
        logging.debug("Cleaning volume stats")

        self._summary_bids_volume_per_interval = 0
        self._summary_asks_volume_per_interval = 0
        self._summary_volume_per_interval = 0
        self._volume_updates_counter_per_interval = 0
