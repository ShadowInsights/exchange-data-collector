# Exchange Data Collector

### Setup .evn

Build .env file from .development.env for local development

### Launch poetry

```sh
poetry shell
```

### Install dependencies

```sh
poetry install
```

### Run Docker to launch ClickHouse

```sh
docker-compose up -d
```

### Run migrations

```sh
poetry run alembic upgrade head
```

### Run the main.py script

```sh
export PYTHONPATH="$PYTHONPATH:$(pwd)"
poetry run python main.py
```

### Run workers

```
export PYTHONPATH="$PYTHONPATH:$(pwd)"
poetry run celery -A app.common.worker.worker worker --loglevel=info
poetry run celery -A app.common.worker.worker beat --loglevel=info
```