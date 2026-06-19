@echo off
echo ========================================================
echo Starting AskDB Backend
echo ========================================================

cd backend

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please run setup_project.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload
