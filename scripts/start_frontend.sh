#!/bin/bash
set -e

echo "========================================================"
echo "Starting AskDB Frontend"
echo "========================================================"

cd frontend

if [ ! -d "node_modules" ]; then
    echo "[ERROR] node_modules not found. Please run setup_project.sh first."
    exit 1
fi

npm run dev
