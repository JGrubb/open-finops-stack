#!/bin/bash

# Start Metabase with DuckDB for FinOps visualization

echo "🚀 Starting Open FinOps Stack visualization layer..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Check if data directory exists
if [ ! -d "./data" ]; then
    echo "📁 Creating data directory..."
    mkdir -p ./data
fi

# Check if DuckDB database exists
if [ ! -f "./data/finops.duckdb" ]; then
    echo "⚠️  Warning: No DuckDB database found at ./data/finops.duckdb"
    echo "   Run './finops aws import-cur' to import some data first"
fi

# Build Metabase with DuckDB driver
echo "🔨 Building Metabase with DuckDB driver..."
docker compose build metabase

# Start services
echo "🎯 Starting services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check if services are running
if docker compose ps | grep -q "metabase.*running"; then
    echo "✅ Metabase is running!"
    echo ""
    echo "📊 Access Metabase at: http://localhost:3000"
    echo ""
    echo "🔧 First time setup:"
    echo "   1. Create your admin account"
    echo "   2. Skip 'Add your data' (we'll configure DuckDB manually)"
    echo "   3. Go to Settings > Admin > Databases > Add database"
    echo "   4. Choose DuckDB and use path: /data/finops.duckdb"
    echo ""
    echo "📈 Your AWS billing data is in schema: aws_billing"
    echo ""
    echo "To view logs: docker compose logs -f metabase"
    echo "To stop: docker compose down"
else
    echo "❌ Failed to start services. Check logs with: docker compose logs"
    exit 1
fi