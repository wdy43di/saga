#!/bin/bash
# backup_secrets.sh — Zips up private Saga data for safe keeping

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_NAME="saga_secrets_$TIMESTAMP.tar.gz"

echo "📦 Packing up the hearth's secrets..."

tar -cvzf "$BACKUP_NAME" \
    saga-core/memory/ \
    saga-core/prompts/saga_system_active.txt \
    ollama/id_ed25519* \
    journal.txt

echo "✅ Backup created: $BACKUP_NAME"
echo "🔐 Keep this file on a thumb drive or private cloud storage."
