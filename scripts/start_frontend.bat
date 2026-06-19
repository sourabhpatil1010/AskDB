@echo off
echo ========================================================
echo Starting AskDB Frontend
echo ========================================================

cd frontend

if not exist "node_modules" (
    echo [ERROR] node_modules not found. Please run setup_project.bat first.
    pause
    exit /b 1
)

call npm run dev
