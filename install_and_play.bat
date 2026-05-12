@echo off
echo ============================================
echo   GESTURE PUZZLE - Hand Gesture Puzzle Game
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Downloading hand tracking model...
if not exist "models" mkdir models
if not exist "models\hand_landmarker.task" (
    curl -L -o models\hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
    if errorlevel 1 (
        echo [WARNING] Could not download model. Game will work without camera.
    ) else (
        echo Model downloaded successfully!
    )
) else (
    echo Model already exists, skipping download.
)

echo.
echo [3/3] Launching game...
echo ============================================
echo   Controls:
echo   - Show hand to webcam to control
echo   - Pinch to grab puzzle pieces
echo   - Open hand to release
echo   - ESC = Pause  ^|  R = Restart  ^|  Q = Quit
echo ============================================
echo.
python run.py
pause
