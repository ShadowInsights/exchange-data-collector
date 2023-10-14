import asyncio
import datetime
import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.database import get_async_db, get_sync_db
from app.db.models.liquidity import Liquidity
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.liquidity_repository import (
    find_last_n_liquidity, find_sync_last_n_liquidity, save_all_liquidity,
    save_liquidity)
from app.db.repositories.order_book_repository import \
    find_all_between_time_range
from app.db.repositories.pair_repository import find_all_pairs, find_pair_by_id
from app.services.collectors.common import Collector
from app.services.collectors.workers.common import Worker
from app.services.collectors.workers.db_worker import set_interval
from app.services.messengers.common import BaseMessage, Field
from app.services.messengers.discord_messenger import DiscordMessenger
from app.utils.math_utils import calc_avg, recalc_avg
from app.utils.string_utils import add_comma_every_n_symbols

NON_EXIST_BEGIN_TIME = datetime.datetime.fromtimestamp(1609459200)


class LiquidityWorker(Worker):
    # TODO: Create a base class for all collectors
    def __init__(self, collector: Collector):
        self._collector = collector
        self._messenger = DiscordMessenger(
            embed_color=settings.DISCORD_DEPTH_EMBED_COLOR
        )

        with get_sync_db() as session:
            # Get last n liquidity records by pair id
            last_liquidity_records = find_sync_last_n_liquidity(
                session,
                self._collector.pair_id,
                settings.COMPARABLE_LIQUIDITY_SET_SIZE,
            )

            # Fill last avg volumes with average volume from extracted liquidity records
            self._last_avg_volumes = [
                liquidity.average_volume
                for liquidity in last_liquidity_records
            ]

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
                self.__send_notification(
                    pair_id=self._collector.pair_id,
                    deviation=deviation,
                    current_avg_volume=self._collector.avg_volume,
                    previous_avg_volume=calc_avg(
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
            calc_avg(
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

    async def __send_notification(
        self,
        pair_id: UUID,
        deviation: float,
        current_avg_volume: int,
        previous_avg_volume: int,
    ) -> None:
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)

        # Formatting message
        title = "Depth Anomaly"

        if deviation < 1:
            depth_change_vector = "Decreased"
        else:
            depth_change_vector = "Increased"

        description = f"{depth_change_vector} depth was detected for **{pair.symbol}** on **{exchange.name}**"
        deviation = Field(name="Deviation", value="{:.2f}".format(deviation))
        volume_changes_field = Field(
            name="Depth changes",
            value=f"Current: {add_comma_every_n_symbols(current_avg_volume)}\nPrevious: "
            f"{add_comma_every_n_symbols(previous_avg_volume)}",
        )

        # Construct message to send
        body = BaseMessage(
            title=title,
            description=description,
            fields=[deviation, volume_changes_field],
        )

        # Sending message
        await self._messenger.send(body)


# TODO: move back to class


async def fill_missed_liquidity_intervals() -> None:
    async with get_async_db() as session:
        pairs = await find_all_pairs(session)

        for pair in pairs:
            # Find latest liquidity record for the specified pair id
            liquidity_entities = await find_last_n_liquidity(
                session, pair.id, 1
            )

    if liquidity_entities is not None and len(liquidity_entities) > 0:
        last_processed_time = liquidity_entities[
            0
        ].created_at + datetime.timedelta(
            seconds=settings.LIQUIDITY_WORKER_JOB_INTERVAL + 1
        )
    else:
        # Set default value
        last_processed_time = NON_EXIST_BEGIN_TIME

    async with get_async_db() as session:
        # Add missed liquidity records between latest liquidity record time and current time
        liquidity_records = await _append_missed_liquidity_records(
            session=session,
            begin_time=last_processed_time,
            pair_id=pair.id,
        )

        await save_all_liquidity(session, liquidity_records=liquidity_records)


async def _append_missed_liquidity_records(
    session: AsyncSession, begin_time: datetime, pair_id: UUID
) -> list[Liquidity]:
    missed_liquidity_records = []

    end_time = datetime.datetime.now() - datetime.timedelta(
        seconds=settings.LIQUIDITY_WORKER_JOB_INTERVAL
    )

    # Fetching unhandled order_books in interval between last liquidity record and time that we already monitor
    order_books = await find_all_between_time_range(
        session,
        begin_time=begin_time,
        end_time=end_time,
        pair_id=pair_id,
    )

    if len(order_books) == 0:
        return []

    # Init avg volume stats
    avg_volume = 0
    volume_counter = 0

    # Calculating and appending average volume with the interval of LIQUIDITY_WORKER_JOB_INTERVAL to the array
    # then to save
    begin_time = order_books[0].created_at
    for order_book in order_books:
        # Parse jsonb order_book field
        data = json.loads(order_book.order_book)

        # Calculating summary volume of order_book
        volume = 0
        for price, quantity in {**data["a"], **data["b"]}.items():
            volume += round(float(price) * float(quantity))

        volume_counter += 1

        end_time = begin_time + datetime.timedelta(
            seconds=settings.LIQUIDITY_WORKER_JOB_INTERVAL
        )

        # Check if the order_book belongs to the next time interval
        if order_book.created_at > end_time:
            # Process average volume of the previous time interval
            missed_liquidity_records.append(
                Liquidity(
                    average_volume=avg_volume,
                    launch_id=order_book.launch_id,
                    pair_id=order_book.pair_id,
                    created_at=begin_time,
                ),
            )

            volume_counter = 1
            avg_volume = recalc_avg(0, volume_counter, volume)
            begin_time = order_book.created_at

        # Process average volume of the current time interval
        avg_volume = recalc_avg(
            avg=avg_volume, counter=volume_counter, value=volume
        )

    # Process average volume of the last time interval
    missed_liquidity_records.append(
        Liquidity(
            average_volume=avg_volume,
            launch_id=order_books[0].launch_id,
            pair_id=order_books[0].pair_id,
            created_at=begin_time,
        )
    )

    return missed_liquidity_records
