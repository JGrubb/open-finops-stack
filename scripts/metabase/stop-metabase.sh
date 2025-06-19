#!/bin/bash
# Stop Metabase gracefully

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

if [ -f "metabase/metabase.pid" ]; then
    PID=$(cat metabase/metabase.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping Metabase (PID: $PID)..."
        kill $PID
        
        # Wait for process to stop
        COUNT=0
        while ps -p $PID > /dev/null 2>&1 && [ $COUNT -lt 30 ]; do
            echo -n "."
            sleep 1
            COUNT=$((COUNT + 1))
        done
        echo ""
        
        if ps -p $PID > /dev/null 2>&1; then
            echo "Process didn't stop gracefully, forcing..."
            kill -9 $PID
        fi
        
        rm metabase/metabase.pid
        echo "Metabase stopped."
    else
        echo "Metabase is not running (stale PID file)"
        rm metabase/metabase.pid
    fi
else
    echo "Metabase is not running (no PID file found)"
fi