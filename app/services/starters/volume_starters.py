import datetime
import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.database import get_async_db
from app.db.models.volume import Volume
from app.db.repositories.order_book_repository import \
    find_all_between_time_range
from app.db.repositories.pair_repository import find_all_pairs_by_maestro_id
from app.db.repositories.volume_repository import (find_last_n_volumes,
                                                   save_all_volumes)
from app.utils.math_utils import recalculate_round_average

NON_EXIST_BEGIN_TIME = datetime.datetime.fromtimestamp(1609459200)


async def fill_missed_volume_intervals(maestro_id: UUID) -> None:
    async with get_async_db() as session:
        pairs = await find_all_pairs_by_maestro_id(session, maestro_id)

        for pair in pairs:
            # Find latest liquidity record for the specified pair id
            liquidity_entities = await find_last_n_volumes(session, pair.id, 1)

    if liquidity_entities is not None and len(liquidity_entities) > 0:
        last_processed_time = liquidity_entities[
            0
        ].created_at + datetime.timedelta(
            seconds=settings.VOLUME_WORKER_JOB_INTERVAL + 1
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

        await save_all_volumes(session, liquidity_records=liquidity_records)


async def _append_missed_liquidity_records(
    session: AsyncSession, begin_time: datetime, pair_id: UUID
) -> list[Volume]:
    missed_liquidity_records = []

    end_time = datetime.datetime.now() - datetime.timedelta(
        seconds=settings.VOLUME_WORKER_JOB_INTERVAL
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
            seconds=settings.VOLUME_WORKER_JOB_INTERVAL
        )

        # Check if the order_book belongs to the next time interval
        if order_book.created_at > end_time:
            # Process average volume of the previous time interval
            missed_liquidity_records.append(
                Volume(
                    average_volume=avg_volume,
                    launch_id=order_book.launch_id,
                    pair_id=order_book.pair_id,
                    created_at=begin_time,
                ),
            )

            volume_counter = 1
            avg_volume = recalculate_round_average(0, volume_counter, volume)
            begin_time = order_book.created_at

        # Process average volume of the current time interval
        avg_volume = recalculate_round_average(
            avg=avg_volume, counter=volume_counter, value=volume
        )

    # Process average volume of the last time interval
    missed_liquidity_records.append(
        Volume(
            average_volume=avg_volume,
            launch_id=order_books[0].launch_id,
            pair_id=order_books[0].pair_id,
            created_at=begin_time,
        )
    )

    return missed_liquidity_records
