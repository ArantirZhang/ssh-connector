#!/bin/bash
# Build script for Linux

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Building SSH Connector for Linux ==="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Build with PyInstaller
echo "Building application..."
pyinstaller \
    --name "ssh-connector" \
    --onefile \
    --add-data "config:config" \
    --hidden-import "paramiko" \
    --hidden-import "PyQt6" \
    src/main.py

echo "=== Build complete ==="
echo "Output: dist/ssh-connector"
