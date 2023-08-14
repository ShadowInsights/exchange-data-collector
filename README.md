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

### Run the main.py script

```sh
export PYTHONPATH="$PYTHONPATH:$(pwd)"
poetry run python main.py
```
