import asyncio
import datetime
import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.database import get_async_db
from app.db.models.liquidity import Liquidity
from app.db.repositories.exchange_repository import find_exchange_by_id
from app.db.repositories.liquidity_repository import (find_last_n_liquidity,
                                                      save_all_liquidity,
                                                      save_liquidity)
from app.db.repositories.order_book_repository import find_all_between
from app.db.repositories.pair_repository import find_all_pairs, find_pair_by_id
from app.services.collectors.workers.db_worker import Worker, set_interval
from app.services.messengers.common import BaseMessage
from app.utils.math_utils import recalc_avg


class LiquidityWorker(Worker):
    def __init__(self, collector):
        self._collector = collector
        self._last_avg_volumes = []

    @set_interval(settings.LIQUIDITY_WORKER_JOB_INTERVAL)
    async def run(self):
        logging.debug("Saving liquidity record")

        async with (get_async_db() as session):
            # Check avg volume for anomaly based on last n avg volumes
            if await self._is_anomaly(session):
                logging.info(
                    f"Found anomaly inflow of volume. Sending alert notification..."
                )

                # Send alert notification via standard messenger implementation
                asyncio.create_task(
                    self._send_notification(pair_id=self._collector.pair_id)
                )

                # Save  runtime liquidity record
                await save_liquidity(
                    session,
                    avg_volume=self._collector.avg_volume,
                    launch_id=self._collector.launch_id,
                    pair_id=self._collector.pair_id,
                )

        self._collector.clear_volume_stats()

    async def _is_anomaly(self, session: AsyncSession) -> bool:
        # if comparable liquidity set size is empty, fill it once from db
        if len(self._last_avg_volumes) == 0:
            # Get last n liquidity records by pair id
            last_liquidity_records = await find_last_n_liquidity(
                session,
                self._collector.pair_id,
                settings.COMPARABLE_LIQUIDITY_SET_SIZE,
            )

            # Fill last avg volumes with average volume from extracted liquidity records
            self._last_avg_volumes = [
                liquidity.average_volume
                for liquidity in last_liquidity_records
            ]

        # if comparable liquidity set size is optimal, then check for anomaly
        if (
            len(self._last_avg_volumes)
            == settings.COMPARABLE_LIQUIDITY_SET_SIZE
        ):
            # Calculate avg volume based on n last volumes
            common_avg_volume = round(
                sum(self._last_avg_volumes)
                / settings.COMPARABLE_LIQUIDITY_SET_SIZE
            )

            # Calculate deviation for avg volume of current time interval in comparison to last n volumes
            deviation = self._collector.avg_volume / common_avg_volume
            logging.debug(
                f"Deviation for {self._collector.avg_volume} volume in comparison to common {common_avg_volume} volume - {deviation}"
            )

            # Update avg volumes queue with last avg volume
            self._last_avg_volumes.pop(0)
            self._last_avg_volumes.append(self._collector.avg_volume)

            # Check if current avg volume is anomaly
            return deviation > settings.LIQUIDITY_ANOMALY_RATIO

        # Fill comparable liquidity set while it will be full, if there's not enough records in db
        self._last_avg_volumes.append(self._collector.avg_volume)

        return False

    async def _send_notification(self, pair_id: UUID):
        async with get_async_db() as session:
            pair = await find_pair_by_id(session, id=pair_id)
            exchange = await find_exchange_by_id(session, id=pair.exchange_id)

            # Formatting message
            title = "Volume Anomaly"
            description = f"Increased volume inflow was detected for {pair.symbol} on {exchange.name}"
            body = BaseMessage(title=title, description=description, fields=[])

            # Sending message
            await self._collector.messenger.send(body)


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
                last_processed_time = datetime.datetime.fromtimestamp(
                    1609459200
                )

            # Add missed liquidity records between latest liquidity record time and current time
            liquidity_records = await _append_missed_liquidity_records(
                session=session,
                begin_time=last_processed_time,
                pair_id=pair.id,
            )

            await save_all_liquidity(
                session, liquidity_records=liquidity_records
            )


async def _append_missed_liquidity_records(
    session: AsyncSession, begin_time: datetime, pair_id: UUID
) -> list[Liquidity]:
    missed_liquidity_records = []

    end_time = datetime.datetime.now() - datetime.timedelta(
        seconds=settings.LIQUIDITY_WORKER_JOB_INTERVAL
    )

    # Fetching unhandled order_books in interval between last liquidity record and time that we already monitor
    order_books = await find_all_between(
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
