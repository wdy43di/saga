#!/bin/bash
# start_saga.sh — Fire up the containers

echo "🔥 Lighting the hearth (Starting Saga containers)..."

# Navigate to the docker directory where your compose file lives
cd ~/saga/docker

# Start the containers in the background
# -d (detached) keeps the containers running even if you close this terminal
docker compose up -d

echo "✅ Saga-Core is running at http://localhost:8000"
echo "✅ Ollama is hidden and humming in the background."
