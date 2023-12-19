import os
import clickhouse_connect


def create_client():
    credentials = dict(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        username=os.getenv("CLICKHOUSE_USERNAME", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        port=os.getenv("CLICKHOUSE_PORT", "8123"),
    )

    client = clickhouse_connect.get_client(**credentials)

    return client
