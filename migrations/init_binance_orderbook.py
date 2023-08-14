import os

from clickhouse_driver import Client


def create_table(client):
    client.execute(
        """
    CREATE TABLE IF NOT EXISTS binance_orderbook
    (
        id UUID,
        launch_id UUID,
        order_type Int8,
        price Decimal256(16),
        quantity Decimal256(16),
        bucket_id UUID,
        pair_id Int16,
        exchange_id Int16,
        stamp_id Int64,
        created_at DateTime
    ) ENGINE = MergeTree()
    ORDER BY (id, created_at)
    """
    )


def main():
    connection_settings = {
        "host": os.getenv("CLICKHOUSE_HOST"),
        "port": int(os.getenv("CLICKHOUSE_PORT")),
        "user": os.getenv("CLICKHOUSE_USERNAME"),
        "password": os.getenv("CLICKHOUSE_PASSWORD"),
        "database": os.getenv("CLICKHOUSE_DATABASE"),
    }
    if int(os.getenv("CLICKHOUSE_PORT")) == 9440:
        connection_settings["secure"] = True
        connection_settings["verify"] = False

    client = Client(**connection_settings)
    create_table(client)


if __name__ == "__main__":
    main()
