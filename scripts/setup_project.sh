#!/bin/bash
set -e

echo "========================================================"
echo "AskDB Project Setup (Linux/Mac)"
echo "========================================================"
echo ""

# 1. Verify Python is installed
echo "[1/11] Verifying Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is not installed or not in PATH."
    exit 1
fi
echo "[OK] Python is installed."

# 2. Verify Node.js is installed
echo "[2/11] Verifying Node.js..."
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed or not in PATH."
    exit 1
fi
echo "[OK] Node.js is installed."

# 3. Verify PostgreSQL is accessible
echo "[3/11] Verifying PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "[ERROR] psql is not recognized. Ensure PostgreSQL is installed."
    exit 1
fi
echo "[OK] PostgreSQL (psql) is accessible."

# 4. Create virtual environment
echo "[4/11] Setting up virtual environment..."
if [ ! -d "backend/venv" ]; then
    python3 -m venv backend/venv
    echo "[OK] Created virtual environment at backend/venv"
else
    echo "[OK] Virtual environment already exists."
fi

# 5. Activate virtual environment
echo "[5/11] Activating virtual environment..."
source backend/venv/bin/activate
echo "[OK] Virtual environment activated."

# 6. Upgrade pip
echo "[6/11] Upgrading pip..."
pip install --upgrade pip > /dev/null
echo "[OK] pip upgraded."

# 7. Install backend dependencies
echo "[7/11] Installing backend dependencies..."
if ! pip install -r backend/requirements.txt; then
    echo "[ERROR] Failed to install backend dependencies."
    exit 1
fi
echo "[OK] Backend dependencies installed."

# 8. Install frontend dependencies
echo "[8/11] Installing frontend dependencies..."
cd frontend
if ! npm install; then
    echo "[ERROR] Failed to install frontend dependencies."
    cd ..
    exit 1
fi
cd ..
echo "[OK] Frontend dependencies installed."

# 9. Verify Alembic is installed
echo "[9/11] Verifying Alembic..."
if ! command -v alembic &> /dev/null; then
    echo "[ERROR] Alembic is not installed in the virtual environment."
    exit 1
fi
echo "[OK] Alembic is installed."

# 10. Run database migrations
echo "[10/11] Running database migrations..."
cd backend
if ! alembic upgrade head; then
    echo "[ERROR] Failed to run database migrations. Ensure PostgreSQL is running and credentials are correct in .env"
    cd ..
    exit 1
fi
cd ..
echo "[OK] Database migrations completed successfully."

# 11. Seed the database
echo "[11/11] Seeding the database..."
cd backend
if ! python3 -m seed.seed_database; then
    echo "[WARNING] Database seeding failed or encountered an issue. It may already be seeded."
else
    echo "[OK] Database seeded successfully."
fi
cd ..

echo ""
echo "========================================================"
echo "[SUCCESS] AskDB project setup is complete!"
echo ""
echo "To start the backend: ./scripts/start_backend.sh"
echo "To start the frontend: ./scripts/start_frontend.sh"
echo "To start both: ./scripts/start_all.sh"
echo "========================================================"
exit 0
