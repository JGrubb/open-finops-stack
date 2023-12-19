import os
import clickhouse_connect
from platformshconfig import Config as PlatformshConfig


def create_client():
    psh_config = PlatformshConfig()
    psh_creds = psh_config.credentials("clickhouse_db")

    credentials = dict(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        username=os.getenv("CLICKHOUSE_USERNAME", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        port=os.getenv("CLICKHOUSE_PORT", "8123"),
    )

    client = clickhouse_connect.get_client(**credentials)

    return client
