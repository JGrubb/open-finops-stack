import clickhouse_connect


def create_client():
    client = clickhouse_connect.get_client(host="localhost", username="default")

    return client
