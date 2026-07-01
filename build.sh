#!/bin/bash
echo "=============================================="
echo "Building J2DM v1.6.8"
echo "=============================================="

echo "[1] Checking for python3..."
if ! command -v python3 &> /dev/null
then
    echo "python3 could not be found. Please install Python 3."
    exit 1
fi

echo "[2] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "[3] Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "[4] Generating icon..."
python3 assets/generate_icon.py || echo "[WARNING] Icon generation failed - building without icon."

echo "[5] Running PyInstaller..."
pyinstaller --noconfirm specs/J2DM-v1.6.8.spec

echo "[6] Cleaning up build files..."
rm -rf build

echo "=============================================="
echo "Build Complete!"
echo "The executable is located in the 'dist' folder."
echo "=============================================="
