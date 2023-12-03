import asyncio
from concurrent.futures import Executor, ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from statistics import mean
from typing import NamedTuple

from app.common.config import settings
from app.common.database import get_async_db
from app.common.processor import Processor
from app.db.models.orders_anomalies_summary import OrdersAnomaliesSummaryModel
from app.db.repositories.order_book_anomaly_repository import (
    get_order_book_anomalies_sum_in_date_range,
)
from app.db.repositories.orders_anomalies_summary_repository import (
    create_orders_anomalies_summary,
    get_latest_orders_anomalies_summary,
)
from app.services.messengers.orders_anomalies_summary_discord_messenger import (
    OrdersAnomaliesSummaryDiscordMessenger,
)
from app.services.workers.common import Worker
from app.utils.math_utils import numbers_have_same_sign
from app.utils.scheduling_utils import SetInterval


class OrdersAnomaliesSummary(NamedTuple):
    current_total_difference: Decimal
    previous_total_difference: Decimal
    deviation: Decimal | None = None


class OrdersAnomaliesSummaryWorker(Worker):
    def __init__(
        self,
        processor: Processor,
        discord_messenger: OrdersAnomaliesSummaryDiscordMessenger,
        volume_anomaly_ratio: float = settings.ORDERS_ANOMALIES_SUMMARY_RATIO,
        volume_comparative_array_size: int = settings.ORDERS_ANOMALIES_SUMMARY_COMPARATIVE_ARRAY_SIZE,
        executor_factory: type[Executor] = ThreadPoolExecutor,
    ):
        super().__init__(processor)
        self._discord_messenger = discord_messenger
        self._volume_anomaly_ratio = Decimal(volume_anomaly_ratio)
        self._volume_comparative_array_size = volume_comparative_array_size + 1
        # TODO: add support for different executor types
        self._executor_factory = executor_factory

    @SetInterval(settings.ORDERS_ANOMALIES_SUMMARY_JOB_INTERVAL)
    async def run(self, callback_event: asyncio.Event | None = None) -> None:
        await super().run(callback_event)
        if callback_event:
            callback_event.set()

    async def _run_worker(self, _: asyncio.Event | None = None) -> None:
        await self.__process_orders_anomalies_summary()

    async def __process_orders_anomalies_summary(self) -> None:
        await self.__create_orders_anomalies_summary()
        await self.__analyze_orders_anomalies_summaries()

    async def __create_orders_anomalies_summary(self) -> None:
        async with get_async_db() as session:
            latest_orders_anomalies_summaries = (
                await get_latest_orders_anomalies_summary(
                    session=session, pair_id=self._processor.pair_id, limit=1
                )
            )
            latest_orders_anomalies_summary_datetime = next(
                (
                    summary.created_at
                    for summary in latest_orders_anomalies_summaries
                ),
                None,
            )

            now_date = datetime.now()
            bids_sum, asks_sum = await asyncio.gather(
                get_order_book_anomalies_sum_in_date_range(
                    session=session,
                    pair_id=self._processor.pair_id,
                    start_datetime=latest_orders_anomalies_summary_datetime,
                    end_datetime=now_date,
                    type="ask",
                ),
                get_order_book_anomalies_sum_in_date_range(
                    session=session,
                    pair_id=self._processor.pair_id,
                    start_datetime=latest_orders_anomalies_summary_datetime,
                    end_datetime=now_date,
                    type="bid",
                ),
            )

            orders_total_difference = bids_sum - asks_sum
            orders_anomalies_summary = OrdersAnomaliesSummaryModel(
                pair_id=self._processor.pair_id,
                launch_id=self._processor.launch_id,
                orders_total_difference=orders_total_difference,
                created_at=now_date,
            )
            await create_orders_anomalies_summary(
                session=session,
                orders_anomalies_summary_in=orders_anomalies_summary,
            )

    async def __analyze_orders_anomalies_summaries(self) -> None:
        async with get_async_db() as session:
            latest_orders_anomalies_summaries = (
                await get_latest_orders_anomalies_summary(
                    session=session,
                    pair_id=self._processor.pair_id,
                    limit=self._volume_comparative_array_size,
                )
            )
        with self._executor_factory() as executor:
            orders_anomalies_summary_deviation = (
                await asyncio.get_event_loop().run_in_executor(
                    executor,
                    self.__perform_anomaly_analysis,
                    latest_orders_anomalies_summaries,
                )
            )

        if orders_anomalies_summary_deviation:
            await self.__send_notification(orders_anomalies_summary_deviation)

    def __perform_anomaly_analysis(
        self,
        latest_orders_anomalies_summaries: list[OrdersAnomaliesSummaryModel],
    ) -> OrdersAnomaliesSummary | None:
        if (
            len(latest_orders_anomalies_summaries)
            < self._volume_comparative_array_size
        ):
            return None

        latest_orders_total_difference_array = [
            summary.orders_total_difference
            for summary in latest_orders_anomalies_summaries[1:]
        ]
        current_total_difference = latest_orders_anomalies_summaries[
            0
        ].orders_total_difference

        previous_orders_total_difference_avg = mean(
            latest_orders_total_difference_array
        )
        if (
            previous_orders_total_difference_avg == 0
            and current_total_difference == 0
        ):
            return None

        if previous_orders_total_difference_avg == 0:
            return OrdersAnomaliesSummary(
                current_total_difference=current_total_difference,
                previous_total_difference=previous_orders_total_difference_avg,
            )

        deviation = (
            current_total_difference / previous_orders_total_difference_avg
        )

        if not numbers_have_same_sign(
            [current_total_difference, previous_orders_total_difference_avg]
        ):
            return OrdersAnomaliesSummary(
                deviation=deviation,
                current_total_difference=current_total_difference,
                previous_total_difference=previous_orders_total_difference_avg,
            )

        if deviation >= self._volume_anomaly_ratio or deviation <= (
            1 / self._volume_anomaly_ratio
        ):
            return OrdersAnomaliesSummary(
                deviation=deviation,
                current_total_difference=current_total_difference,
                previous_total_difference=previous_orders_total_difference_avg,
            )

        return None

    async def __send_notification(
        self, orders_anomalies_summary_deviation: OrdersAnomaliesSummary
    ) -> None:
        await self._discord_messenger.send_notification(
            pair_id=self._processor.pair_id,
            deviation=orders_anomalies_summary_deviation.deviation,
            current_total_difference=orders_anomalies_summary_deviation.current_total_difference,
            previous_total_difference=orders_anomalies_summary_deviation.previous_total_difference,
        )
