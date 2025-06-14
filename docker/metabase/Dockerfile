FROM metabase/metabase:latest

# Download and install the official MotherDuck DuckDB driver
# Check for latest version at: https://github.com/MotherDuck-Open-Source/metabase_duckdb_driver/releases
ADD https://github.com/MotherDuck-Open-Source/metabase_duckdb_driver/releases/download/v0.10.1/duckdb.metabase-driver.jar /plugins/

# Ensure correct permissions
RUN chmod 744 /plugins/duckdb.metabase-driver.jar