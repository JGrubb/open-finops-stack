#!/bin/bash
# Run Metabase natively on macOS connecting to Podman PostgreSQL

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Create directories if they don't exist
mkdir -p logs metabase/plugins

# Check if Metabase JAR exists
if [ ! -f "metabase/metabase.jar" ]; then
    echo "Metabase JAR not found. Downloading..."
    curl -L https://downloads.metabase.com/v0.50.26/metabase.jar -o metabase/metabase.jar
fi

# Check if DuckDB driver exists
if [ ! -f "metabase/plugins/duckdb.metabase-driver.jar" ]; then
    echo "DuckDB driver not found. Downloading..."
    curl -L https://github.com/MotherDuck-Open-Source/metabase_duckdb_driver/releases/download/0.3.1/duckdb.metabase-driver.jar \
         -o metabase/plugins/duckdb.metabase-driver.jar
fi

# Set environment variables for Metabase
export MB_DB_TYPE=postgres
export MB_DB_DBNAME=metabase
export MB_DB_PORT=5432
export MB_DB_USER=metabase
export MB_DB_PASS=metabase
export MB_DB_HOST=localhost
export MB_PLUGINS_DIR="$PROJECT_ROOT/metabase/plugins"

# Function to start Metabase
start_metabase() {
    echo "Starting Metabase with PostgreSQL backend..."
    echo "PostgreSQL should be running at localhost:5432"
    echo "DuckDB database is at: $PROJECT_ROOT/data/finops.duckdb"
    echo "Logs will be written to: $PROJECT_ROOT/logs/metabase.log"
    echo ""
    
    # Run Metabase in background with logging
    nohup java -jar metabase/metabase.jar > logs/metabase.log 2>&1 &
    METABASE_PID=$!
    
    echo "Metabase started with PID: $METABASE_PID"
    echo "PID written to: $PROJECT_ROOT/metabase/metabase.pid"
    echo $METABASE_PID > metabase/metabase.pid
    
    echo ""
    echo "Metabase will be available at: http://localhost:3000"
    echo "To view logs: tail -f logs/metabase.log"
    echo "To stop: ./scripts/metabase/stop-metabase.sh"
}

# Function to check if Metabase is already running
check_running() {
    if [ -f "metabase/metabase.pid" ]; then
        PID=$(cat metabase/metabase.pid)
        if ps -p $PID > /dev/null 2>&1; then
            echo "Metabase is already running with PID: $PID"
            echo "To stop it, run: ./scripts/metabase/stop-metabase.sh"
            exit 1
        else
            # PID file exists but process is not running
            rm metabase/metabase.pid
        fi
    fi
}

# Main execution
check_running
start_metabase