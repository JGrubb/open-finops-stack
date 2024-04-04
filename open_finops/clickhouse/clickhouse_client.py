import os
import clickhouse_connect
from clickhouse_connect.driver.exceptions import OperationalError
from platformshconfig import Config as PlatformshConfig


def create_client(settings=None):
    try:
        psh_config = PlatformshConfig()
        psh_creds = psh_config.credentials("clickhouse_db")
    except Exception as e:
        psh_creds = None

    if psh_creds:
        credentials = dict(
            host=psh_creds["host"],
            username=psh_creds["username"],
            password=psh_creds["password"],
            port=psh_creds["port"],
            settings=settings,
        )
    else:
        credentials = dict(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            username=os.getenv("CLICKHOUSE_USERNAME", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            port=os.getenv("CLICKHOUSE_PORT", "8123"),
            settings=settings,
        )
    try:
        client = clickhouse_connect.get_client(**credentials)
    except OperationalError as e:
        print(e)
        raise SystemExit

    return client
