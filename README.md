# Exchange Data Collector

### Setup .evn

Build .env file from .development.env for local development.

### Launch poetry

```sh
poetry shell
```

### Install dependencies

```sh
poetry install
```

### Run migrations

```sh
poetry run alembic upgrade head
```

### Run the application

```sh
python -m app.main
```

### Run the application with dubug mode

```sh
python -m app.main --debug
```