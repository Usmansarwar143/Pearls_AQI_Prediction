@echo off
title Pearls AQI Predictor
echo ==============================================
echo      Starting Pearls AQI Predictor
echo ==============================================
echo.

:: Check if virtual environment exists
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found.
    echo [INFO] Creating virtual environment 'venv'...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment. Please ensure Python is installed and added to PATH.
        pause
        exit /b 1
    )
    
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
    
    echo [INFO] Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
    echo [INFO] Setup complete.
) ELSE (
    echo [INFO] Activating existing virtual environment...
    call venv\Scripts\activate.bat
)

echo.
echo [INFO] Launching the application...
echo [INFO] The dashboard will open in your default browser shortly.
echo [INFO] To stop the server, press Ctrl+C or close this window.
echo.

:: Open browser after a slight delay
start "" cmd /c "timeout /t 3 >nul & start http://localhost:8000/"

:: Start the FastAPI backend and serve frontend
python -m uvicorn src.web_app.backend_api:app --host 0.0.0.0 --port 8000 --reload

pause
