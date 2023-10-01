import logging
from datetime import datetime
from typing import Iterator, List

from celery_once import QueueOnce
from google.cloud import storage
from sqlalchemy.orm.session import Session

from app.common.config import celery, settings
from app.common.database import get_sync_db
from app.db.models.order_book import OrderBookModel

storage_client = storage.Client()
logger = logging.getLogger(__name__)


def _fetch_data(
    session: Session, limit: int, offset: int
) -> List[OrderBookModel]:
    return session.query(OrderBookModel).limit(limit).offset(offset).all()


def _row_to_csv(row: OrderBookModel) -> str:
    return f"{row.id},{row.launch_id},{row.stamp_id},{row.order_book},{row.pair_id},{row.created_at}\n"


def _buffered_rows_generator(session: Session) -> Iterator[str]:
    offset = 0
    while True:
        results = _fetch_data(
            session, settings.ORDER_BOOKS_TABLE_DUMP_LIMIT, offset
        )
        if not results:
            break
        for row in results:
            yield _row_to_csv(row)
        offset += settings.ORDER_BOOKS_TABLE_DUMP_LIMIT


def _chunks(data: Iterator[str], buffer_max_size: int) -> Iterator[List[str]]:
    buffer = []
    for item in data:
        buffer.append(item)
        if len(buffer) >= buffer_max_size:
            yield buffer
            buffer = []
    if buffer:
        yield buffer


def _upload_to_gcs(data: List[str], blob) -> None:
    blob.upload_from_string(
        "".join(data), content_type="text/csv", if_generation_match=0
    )


@celery.task(base=QueueOnce, once={"graceful": True})
def order_book_table_truncate_and_backup():
    total_rows = 0
    bucket = storage_client.bucket(settings.GOOGLE_CLOUD_BUCKET_NAME)
    blob = bucket.blob(f"order-books-dump-{datetime.utcnow()}.csv")
    with get_sync_db() as session:
        for buffer in _chunks(
            _buffered_rows_generator(session),
            settings.ORDER_BOOKS_TABLE_DUMP_BUFFER_MAX_SIZE,
        ):
            _upload_to_gcs(buffer, blob)
            total_rows += len(buffer)
            logger.info(f"Uploaded {total_rows} rows so far...")
        logger.info(f"Total rows uploaded: {total_rows}")
