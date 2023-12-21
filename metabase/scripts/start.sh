#!/bin/sh

# Load header
. ./header.inc

# Port to Listen on
export MB_JETTY_PORT=${PORT}

# Database Conection Info
export MB_DB_TYPE=postgres
export MB_DB_DBNAME=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r .metabasedb[0].path)
export MB_DB_PORT=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq  -r .metabasedb[0].port)
export MB_DB_USER=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq  -r .metabasedb[0].username)
export MB_DB_PASS=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r .metabasedb[0].password)
export MB_DB_HOST=$(echo $PLATFORM_RELATIONSHIPS | base64 --decode | jq -r .metabasedb[0].host)

# Email
export MB_EMAIL_SMTP_HOST=$PLATFORM_SMTP_HOST
export MB_EMAIL_SMTP_PORT=25
export MB_EMAIL_SMTP_USERNAME=""
export MB_EMAIL_SMTP_PASSWORD=""

# Grab memory limits
export MEM_AVAILABLE=$(bin/jq .info.limits.memory /run/config.json)

# Limit Heapsize
export JAVA_TOOL_OPTIONS="-XX:+CMSClassUnloadingEnabled -XX:+UseConcMarkSweepGC -XX:MaxPermSize=${MEM_AVAILABLE}m -Xmx${MEM_AVAILABLE}m"

# This ensures that the child process below gets stopped when Platform.sh kills this script.
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

#java -jar ${METABASE_HOME}/${METABASE_JAR} migrate release-locks
exec java -jar ${METABASE_HOME}/${METABASE_JAR}
