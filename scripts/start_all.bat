@echo off
echo ========================================================
echo Starting AskDB Project (All Services)
echo ========================================================

:: Check if scripts exist
if not exist "scripts\start_backend.bat" (
    echo [ERROR] start_backend.bat not found in scripts directory.
    pause
    exit /b 1
)

if not exist "scripts\start_frontend.bat" (
    echo [ERROR] start_frontend.bat not found in scripts directory.
    pause
    exit /b 1
)

echo Starting Backend in a new terminal window...
start "AskDB Backend" cmd /k "call scripts\start_backend.bat"

echo Starting Frontend in a new terminal window...
start "AskDB Frontend" cmd /k "call scripts\start_frontend.bat"

echo.
echo Both services have been started in separate windows.
echo Close this window at any time.
