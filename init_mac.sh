#!/bin/bash

# Database initialization script for Mac/Linux
# This script runs Alembic migrations and initializes the database with default data

set -e

echo "🚀 Starting database initialization..."

# Check if podman/docker is running
if ! command -v podman &> /dev/null && ! command -v docker &> /dev/null; then
    echo "❌ Error: Neither podman nor docker is installed"
    exit 1
fi

# Use podman if available, otherwise docker
CONTAINER_CMD="podman"
if ! command -v podman &> /dev/null; then
    CONTAINER_CMD="docker"
fi

echo "📦 Using container runtime: $CONTAINER_CMD"

# Check if backend container is running
if ! $CONTAINER_CMD ps | grep -q pca-backend; then
    echo "❌ Error: Backend container is not running"
    echo "Please start the containers first using: ./start_all.sh"
    exit 1
fi

echo "⏳ Running Alembic migrations..."
$CONTAINER_CMD exec pca-backend-1 alembic upgrade head

echo "⏳ Initializing database with default data..."
$CONTAINER_CMD exec pca-backend-1 python init_db.py

echo ""
echo "✅ Database initialization complete!"
echo ""
echo "📝 You can now login with:"
echo "   Username: superadmin"
echo "   Password: superadmin123"
echo ""
echo "🌐 Access the application at: http://localhost:3001"
