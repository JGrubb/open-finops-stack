FROM metabase/metabase:latest

# Install required C++ libraries for DuckDB
USER root
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Download and install the official MotherDuck DuckDB driver
# Check for latest version at: https://github.com/MotherDuck-Open-Source/metabase_duckdb_driver/releases
ADD https://github.com/MotherDuck-Open-Source/metabase_duckdb_driver/releases/download/0.3.1/duckdb.metabase-driver.jar /plugins/

# Ensure correct permissions
RUN chmod 744 /plugins/duckdb.metabase-driver.jar

# Switch back to metabase user
USER metabase