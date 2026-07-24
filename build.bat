@echo off
echo ==============================================
echo Building J2DM v1.6.11
echo ==============================================

echo [1] Checking for python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [2] Creating virtual environment...
if not exist venv (
    python -m venv venv
)

echo [3] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo [4] Generating icon...
python assets\generate_icon.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Icon generation failed - building without icon.
)

echo [5] Running PyInstaller...
set "SPEC_FILE=specs\J2DM-v1.6.11.spec"
echo Compiling the executable...
pyinstaller --noconfirm "%SPEC_FILE%"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller failed!
    exit /b %ERRORLEVEL%
)

echo [6] Cleaning up build files...
rmdir /S /Q build

echo ==============================================
echo Build Complete!
echo The executable is located in the 'dist' folder.
echo ==============================================
pause
