#!/bin/bash

# Local.
if [ -z ${PLATFORM_PROJECT_ENTROPY+x} ]; then 
    echo "Building Metabase locally"
    METABASE_HOME=$(pwd)/metabase
    echo "Metabase home: $METABASE_HOME"
# Platform.sh.
else
    echo "Building Metabase on Platform.sh"
    METABASE_HOME=${PLATFORM_APP_DIR}/metabase
fi

    METABASE_VERSION="0.47.10"

# Download Metabase.
echo "Downloading Metabase ($METABASE_VERSION)"
wget --no-cookies --no-check-certificate -q -O \
    "$METABASE_HOME/metabase.jar" "http://downloads.metabase.com/$METABASE_VERSION/metabase.jar"