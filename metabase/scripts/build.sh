#!/bin/bash

# Load header
. ./scripts/header.inc

# Desired version can be set by means of an enviromental variable
if [ -z "$METABASE_VERSION" ]; then 
	METABASE_VERSION=0.47.10;
fi

METABASE_DOWNLOAD_URI="http://downloads.metabase.com/v${METABASE_VERSION}"
METABASE_DL_ARCHIVE="metabase.jar"

# Make directories
mkdir -p $METABASE_HOME bin;

# Download Metabase
echo "Downloading ${METABASE_DOWNLOAD_URI}/${METABASE_DL_ARCHIVE}"
wget --no-cookies --no-check-certificate -q -O ${METABASE_HOME}/${METABASE_JAR} ${METABASE_DOWNLOAD_URI}/${METABASE_DL_ARCHIVE}

# jq is a command line utility to parse JSON data
# Desired version can be set using an environment variable
if [ -z "$JQ_VERSION" ]; then 
	# Default to version 1.7
    JQ_VERSION=1.7
fi

# Download and put it in the bin folder
JQ_DOWNLOAD_URI="https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}"
JQ_DL_ARCHIVE="jq-linux64"

echo "Downloading ${JQ_DOWNLOAD_URI}/${JQ_DL_ARCHIVE}"
wget ${JQ_DOWNLOAD_URI}/${JQ_DL_ARCHIVE} --no-cookies --no-check-certificate -q -O bin/jq
chmod +x bin/jq
