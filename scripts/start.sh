#!/bin/bash
# start.sh — Build and start the restaurant agent stack
# Uses docker compose (works with both Docker and OrbStack)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check for .env
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and fill in your keys."
    echo "  cp .env.example .env"
    exit 1
fi

echo "Building containers..."
docker compose build

echo "Starting services..."
docker compose up -d

echo ""
echo "✅ Restaurant Agent is running!"
echo "   Agent API:  http://localhost:8000"
echo "   Dashboard:  http://localhost:8501"
echo "   Health:     http://localhost:8000/health"
echo ""
echo "To view logs:  docker compose logs -f"
echo "To stop:       docker compose down"
