@echo off
title Pearls AQI Predictor
echo ==============================================
echo      Starting Pearls AQI Predictor
echo ==============================================
echo.

:: Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python from https://www.python.org/downloads/ and check "Add Python to PATH".
    pause
    exit /b 1
)

:: Check if virtual environment exists
IF NOT EXIST "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found.
    echo [INFO] Creating virtual environment 'venv'...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    
    echo [INFO] Upgrading pip...
    venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
    
    echo [INFO] Installing dependencies from requirements.txt...
    venv\Scripts\pip.exe install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
    echo [INFO] Setup complete.
) ELSE (
    echo [INFO] Found existing virtual environment.
)

echo.
echo [INFO] Launching the application...
echo [INFO] The dashboard will open in your default browser shortly.
echo [INFO] To stop the server, press Ctrl+C or close this window.
echo.

:: Open browser
start http://localhost:8000/

:: Start the FastAPI backend and serve frontend
venv\Scripts\python.exe -m uvicorn src.web_app.backend_api:app --host 0.0.0.0 --port 8000 --reload

pause
