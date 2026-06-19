#!/bin/bash
set -e

echo "========================================================"
echo "Starting AskDB Backend"
echo "========================================================"

cd backend

if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found. Please run setup_project.sh first."
    exit 1
fi

source venv/bin/activate
python3 -m uvicorn app.main:app --reload
