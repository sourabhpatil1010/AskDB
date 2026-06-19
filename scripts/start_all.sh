#!/bin/bash

echo "========================================================"
echo "Starting AskDB Project (All Services)"
echo "========================================================"

# Function to cleanup background processes on script exit
cleanup() {
    echo ""
    echo "Stopping AskDB Services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT SIGTERM

if [ ! -f "scripts/start_backend.sh" ]; then
    echo "[ERROR] start_backend.sh not found."
    exit 1
fi

if [ ! -f "scripts/start_frontend.sh" ]; then
    echo "[ERROR] start_frontend.sh not found."
    exit 1
fi

# Ensure scripts are executable
chmod +x scripts/start_backend.sh
chmod +x scripts/start_frontend.sh

echo "Starting Backend in the background..."
./scripts/start_backend.sh &
BACKEND_PID=$!

echo "Starting Frontend..."
./scripts/start_frontend.sh &
FRONTEND_PID=$!

echo "Both services are running. Press Ctrl+C to stop both."
wait $BACKEND_PID $FRONTEND_PID
