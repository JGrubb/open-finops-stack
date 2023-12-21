#!/bin/sh

tunnel_to_db () {
    # Open a local tunnel to the environment.
    platform tunnel:close -y
    platform tunnel:open -y

    # Mock PLATFORM_RELATIONSHIPS variable locally. 
    export PLATFORM_RELATIONSHIPS="$(platform tunnel:info --encode)"
}

# Local.
if [ -z ${PLATFORM_PROJECT_ENTROPY+x} ]; then 
    export MB_JETTY_PORT=8888

    # Open a tunnel to the current service.
    tunnel_to_db

    # Set database connection variables.
    export MB_DB_TYPE=postgres
    export MB_DB_DBNAME=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r ".database[0].path")
    export MB_DB_HOST=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r ".database[0].host")
    export MB_DB_PORT=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r ".database[0].port")
    export MB_DB_USER=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r ".database[0].username")
    export MB_DB_PASS=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r ".database[0].password")

    # Limit heap size
    export JAVA_TOOL_OPTIONS="-Xmx500m -XX:+ExitOnOutOfMemoryError -Xlog:gc*"
    export JAR_FILE=$(pwd)/metabase/metabase.jar

# Platform.sh.
else 
    export JAR_FILE=$PLATFORM_APP_DIR/metabase/metabase.jar
fi

java -jar $JAR_FILE