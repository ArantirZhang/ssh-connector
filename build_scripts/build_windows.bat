@echo off
REM Build script for Windows

echo === Building SSH Connector for Windows ===

cd /d "%~dp0\.."

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Build with PyInstaller
echo Building application...
pyinstaller ^
    --name "SSH Connector" ^
    --windowed ^
    --onefile ^
    --icon "src\ui\resources\icon.ico" ^
    --add-data "config;config" ^
    --hidden-import "paramiko" ^
    --hidden-import "PyQt6" ^
    src\main.py

echo === Build complete ===
echo Output: dist\SSH Connector.exe
