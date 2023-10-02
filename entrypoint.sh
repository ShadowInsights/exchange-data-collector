#!/bin/sh
# entrypoint.sh

celery -A app.common.worker.worker worker --loglevel=info &
celery -A app.common.worker.worker beat --loglevel=info &
python /home/app/app/main.py
