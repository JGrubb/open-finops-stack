
set -e

# Get the current, and latest upstream version of Metabase.
CURRENT_VERSION=$(cat metabase.version)
LATEST_VERSION=$(curl -s https://api.github.com/repos/metabase/metabase/releases/latest | jq -r '.tag_name')

# If updates available, modify metabase.version.
if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "You are using the latest version of Metabase."
else
    echo "Update found for Metabase: $CURRENT_VERSION -> $LATEST_VERSION."
    echo "Applying update."
    echo $LATEST_VERSION > metabase.version
fi

# Stage changes (on Platform.sh source operation), committing only when updates are available.
if [ ! -z ${PLATFORM_PROJECT_ENTROPY+x} ]; then 
    git add .
    STAGED_UPDATES=$(git diff --cached)
    if [ ${#STAGED_UPDATES} -gt 0 ]; then
        git commit -m "Upgrade Metabase: $CURRENT_VERSION -> $LATEST_VERSION."
    else
        echo "No updates needed. Skipping."
    fi
fi