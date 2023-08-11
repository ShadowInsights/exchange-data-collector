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
    client = Client(
        host=os.getenv("CLICKHOUSE_HOST"), port=os.getenv("CLICKHOUSE_PORT")
    )
    create_table(client)


if __name__ == "__main__":
    main()
