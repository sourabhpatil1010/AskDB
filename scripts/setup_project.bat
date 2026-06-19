@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo AskDB Project Setup (Windows)
echo ========================================================
echo.

:: 1. Verify Python is installed
echo [1/11] Verifying Python...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.10+ and try again.
    exit /b 1
)
echo [OK] Python is installed.

:: 2. Verify Node.js is installed
echo [2/11] Verifying Node.js...
node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH. Please install Node.js and try again.
    exit /b 1
)
echo [OK] Node.js is installed.

:: 3. Verify PostgreSQL is accessible
echo [3/11] Verifying PostgreSQL...
psql -V >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] psql is not recognized. Ensure PostgreSQL is installed and psql is in your PATH.
    exit /b 1
)
echo [OK] PostgreSQL (psql) is accessible.

:: 4. Create virtual environment
echo [4/11] Setting up virtual environment...
if not exist "backend\venv" (
    python -m venv backend\venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
    echo [OK] Created virtual environment at backend\venv
) else (
    echo [OK] Virtual environment already exists.
)

:: 5. Activate virtual environment
echo [5/11] Activating virtual environment...
call backend\venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    exit /b 1
)
echo [OK] Virtual environment activated.

:: 6. Upgrade pip
echo [6/11] Upgrading pip...
python -m pip install --upgrade pip >nul
echo [OK] pip upgraded.

:: 7. Install backend dependencies
echo [7/11] Installing backend dependencies...
pip install -r backend\requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install backend dependencies.
    exit /b 1
)
echo [OK] Backend dependencies installed.

:: 8. Install frontend dependencies
echo [8/11] Installing frontend dependencies...
pushd frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install frontend dependencies.
    popd
    exit /b 1
)
popd
echo [OK] Frontend dependencies installed.

:: 9. Verify Alembic is installed
echo [9/11] Verifying Alembic...
alembic --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Alembic is not installed in the virtual environment.
    exit /b 1
)
echo [OK] Alembic is installed.

:: 10. Run database migrations
echo [10/11] Running database migrations...
pushd backend
alembic upgrade head
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to run database migrations. Ensure PostgreSQL is running and credentials are correct.
    popd
    exit /b 1
)
popd
echo [OK] Database migrations completed successfully.

:: 11. Seed the database
echo [11/11] Seeding the database...
pushd backend
python -m seed.seed_database
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Database seeding failed or encountered an issue. It may already be seeded.
) else (
    echo [OK] Database seeded successfully.
)
popd

echo.
echo ========================================================
echo [SUCCESS] AskDB project setup is complete!
echo.
echo To start the backend: run scripts\start_backend.bat
echo To start the frontend: run scripts\start_frontend.bat
echo To start both: run scripts\start_all.bat
echo ========================================================
exit /b 0
