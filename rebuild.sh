#!/bin/bash
# rebuild.sh — Fully rebuild and launch Saga via Docker Compose

# Exit immediately if a command fails
set -e

echo "🧹 Clearing old embers (Stopping containers)..."
# Navigate to the docker directory where the compose file lives
cd ~/saga/docker

# 'down' removes containers and networks defined in the compose file
docker compose down --remove-orphans

echo "🏗️ Forging the Core (Building Saga-Core)..."
# '--no-cache' ensures a fresh build of your Python environment
# '--build' tells compose to build images before starting containers
docker compose up -d --build

echo "⏳ Waiting for the hearth to catch (Giving Ollama a moment)..."
sleep 5

# Optional: Check if the model is already there, if not, pull it.
# This prevents the 'Model not found' error on first run.
echo "🔍 Checking for Llama3..."
docker exec saga-ollama ollama pull llama3:latest

echo "------------------------------------------------"
echo "✅ Saga is reborn."
echo "🌐 Web UI: http://localhost:8000"
echo "📜 Persona: ~/saga/saga-core/prompts/saga_system_active.txt"
echo "------------------------------------------------"

# Show the status of the containers
docker compose ps
