#!/usr/bin/env bash
set -e

echo "🛑 Stopping Saga (if running)..."
docker stop saga-core 2>/dev/null || true

echo "🧹 Removing old container..."
docker rm saga-core 2>/dev/null || true

echo "🔨 Rebuilding saga-core image..."
docker build -t saga-core ./saga-core

echo "🚀 Starting Saga..."
docker run -d \
  --name saga-core \
  --network saga-net \
  -p 11434:11434 \
  -v "$HOME/saga/saga-core/memory:/saga/memory" \
  saga-core

echo "✅ Saga reset complete"
