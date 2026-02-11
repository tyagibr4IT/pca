#!/bin/bash

# Start script for Mac/Linux

set -e

cd "$(dirname "$0")"

echo "Starting PCA stack..."

# Use podman if available, otherwise docker
CONTAINER_CMD="podman"
if ! command -v podman &> /dev/null; then
    if command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
    else
        echo "❌ Error: Neither podman nor docker is installed"
        exit 1
    fi
fi

echo "📦 Using container runtime: $CONTAINER_CMD"

# Use docker-compose or podman-compose
if [ "$CONTAINER_CMD" = "podman" ]; then
    COMPOSE_CMD="podman compose"
else
    COMPOSE_CMD="docker compose"
fi

$COMPOSE_CMD -f podman-compose.yml up -d --remove-orphans

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Stack started successfully!"
    echo ""
    echo "🌐 Frontend: http://localhost:3001"
    echo "🔧 Backend:  http://localhost:8001"
    echo ""
    echo "📝 If this is your first time, run: ./init_mac.sh"
else
    echo "❌ Error starting containers"
    exit 1
fi
