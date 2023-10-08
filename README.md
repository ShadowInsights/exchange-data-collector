# Exchange Data Collector

### Setup .evn

Build .env file from .development.env for local development
Removed PYTHON_ENV=DEV from .env file for production environment

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

### Run the application

```sh
export PYTHONPATH="$PYTHONPATH:$(pwd)"
poetry run python ./app/main.py
```