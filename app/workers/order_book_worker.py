import logging
from datetime import datetime
from typing import Iterator, List

from google.cloud import storage
from google.cloud.storage import Blob, Bucket
from sqlalchemy.orm.session import Session

from app.common.config import settings
from app.common.database import get_sync_db
from app.db.models.order_book import OrderBookModel

logger = logging.getLogger(__name__)


class BlobMalformed(Exception):
    pass


def _fetch_data(
    session: Session, limit: int, offset: int
) -> List[OrderBookModel]:
    return (
        session.query(OrderBookModel)
        .order_by(OrderBookModel.created_at.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )


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


def _upload_to_gcs(data: List[str], bucket: Bucket, blob_name: str) -> None:
    temp_blob_name = f"{blob_name}-temp-{datetime.utcnow().timestamp()}"
    temp_blob = bucket.blob(temp_blob_name)
    temp_blob.upload_from_string("".join(data), content_type="text/csv")

    original_blob = bucket.get_blob(blob_name)
    if original_blob:
        composed_blob = Blob(blob_name, bucket)
        composed_blob.compose([original_blob, temp_blob])
    else:
        logger.info(f"Creating new blob: {blob_name}")
        bucket.copy_blob(temp_blob, bucket, blob_name)

    temp_blob.delete()


def order_book_table_truncate_and_backup() -> None:
    logger.info("Starting order book table backup...")

    total_rows = 0

    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.GOOGLE_CLOUD_BUCKET_NAME)
    blob_name = f"order-books-{datetime.utcnow().strftime('%Y-%m-%d')}.csv"

    with get_sync_db() as session:
        logger.info("Starting to fetch data from the database...")

        for buffer in _chunks(
            _buffered_rows_generator(session),
            settings.ORDER_BOOKS_TABLE_DUMP_BUFFER_MAX_SIZE,
        ):
            _upload_to_gcs(buffer, bucket, blob_name)
            total_rows += len(buffer)
            logger.info(f"Uploaded {total_rows} rows so far...")

        logger.info(f"Total rows uploaded: {total_rows}")

        try:
            # TODO: This will cause issue if the table is too big, fix it later
            session.query(OrderBookModel).delete()
            session.commit()
            logger.info("Successfully truncated the OrderBookModel table")
        except Exception as e:
            logger.error(
                f"Failed to truncate the OrderBookModel table. Reason: {str(e)}"
            )
            session.rollback()
