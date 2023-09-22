import os

from clickhouse_driver import Client


def create_table(client):
    client.execute(
        """
    SET allow_create_index_without_type=1;
    ALTER TABLE binance_orderbook ADD INDEX launch_id_index (launch_id) TYPE minmax GRANULARITY 1;
    ALTER TABLE binance_orderbook ADD INDEX stamp_id_index (stamp_id) TYPE minmax GRANULARITY 1;
    ALTER TABLE binance_orderbook ADD INDEX bucket_id_index (bucket_id) TYPE minmax GRANULARITY 1;
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
