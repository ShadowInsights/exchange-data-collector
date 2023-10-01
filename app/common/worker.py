from celery.schedules import crontab

from app.common.config import celery as worker
from app.workers.order_book_worker import order_book_table_truncate_and_backup

worker.conf.beat_schedule = {
    "order-book-table-truncate-and-backup-daily-at-23-utc": {
        "task": order_book_table_truncate_and_backup.name,
        "schedule": crontab(hour=22, minute=30),
    },
}
