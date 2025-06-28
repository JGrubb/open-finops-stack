# ClickHouse Backend Implementation

This document details the design and implementation of the ClickHouse backend for the Open FinOps stack.

## Overview

The ClickHouse backend provides a high-performance, scalable, and open-source alternative to the default DuckDB backend. It is designed for large-scale data storage and analytics, making it suitable for production environments with substantial FinOps data.

The implementation leverages ClickHouse's native S3 integration capabilities for efficient data loading and a custom state management system to track data ingestion progress.

## Key Components

-   **`ClickHouseBackend`**: The main backend class that implements the `DatabaseBackend` interface. It handles the connection to ClickHouse and provides the `dlt` destination.
-   **`ClickHouseStateManager`**: Implements the `StateManager` interface. It creates and manages a `load_state` table in ClickHouse to track the status of data loads, prevent duplicates, and manage data versions.
-   **`ClickHouseConfig`**: A dataclass that holds the configuration parameters for the ClickHouse connection.
-   **Backend Factory Integration**: The backend is registered in the `core.backends.factory` to be dynamically loaded based on the configuration.

## Configuration

To use the ClickHouse backend, modify your `config.toml` file to include a `[database.clickhouse]` section:

```toml
[database]
backend = "clickhouse"

[database.clickhouse]
host = "localhost"
port = 8123
database = "finops"
user = "default"
password = ""
```

### Parameters

-   `backend`: Must be set to `"clickhouse"`.
-   `host`: The hostname or IP address of your ClickHouse server.
-   `port`: The HTTP/HTTPS port of your ClickHouse server (default is 8123).
-   `database`: The name of the database to use for FinOps data.
-   `user`: The username for the ClickHouse connection.
-   `password`: The password for the ClickHouse connection.

## State Management

The `ClickHouseStateManager` creates a table named `load_state` in the specified database. This table tracks every data load attempt and its status (`started`, `completed`, `failed`).

The table schema is as follows:

```sql
CREATE TABLE finops.load_state (
    vendor String,
    export_name String,
    billing_period String,
    version_id String,
    data_format_version String,
    file_count UInt32,
    row_count UInt64,
    status String,
    error_message String,
    started_at DateTime,
    completed_at DateTime,
    is_current UInt8
) ENGINE = MergeTree()
ORDER BY (vendor, export_name, billing_period, started_at)
```

This allows for robust and auditable data ingestion pipelines.

## Usage

Once the configuration is set, the Open FinOps CLI will automatically use the ClickHouse backend for all operations, including `aws import-cur`. Data will be loaded directly into your ClickHouse instance.

## Dependencies

The following Python packages are required for the ClickHouse backend:

-   `dlt[clickhouse]`
-   `clickhouse-connect`

These are included in `requirements.txt`.
