#!/bin/bash
echo "============================================"
echo "  GESTURE PUZZLE - Hand Gesture Puzzle Game"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed!"
    echo "Install it with: sudo apt install python3 python3-pip (Ubuntu/Debian)"
    echo "                 brew install python3 (macOS)"
    exit 1
fi

echo "[1/3] Installing dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi

echo ""
echo "[2/3] Downloading hand tracking model..."
mkdir -p models
if [ ! -f "models/hand_landmarker.task" ]; then
    curl -L -o models/hand_landmarker.task \
        https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
    if [ $? -ne 0 ]; then
        echo "[WARNING] Could not download model. Game will work without camera."
    else
        echo "Model downloaded successfully!"
    fi
else
    echo "Model already exists, skipping download."
fi

echo ""
echo "[3/3] Launching game..."
echo "============================================"
echo "  Controls:"
echo "  - Show hand to webcam to control"
echo "  - Pinch to grab puzzle pieces"
echo "  - Open hand to release"
echo "  - ESC = Pause  |  R = Restart  |  Q = Quit"
echo "============================================"
echo ""
python3 run.py
