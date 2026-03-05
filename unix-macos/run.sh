#!/bin/bash

# Switch to the project root directory
cd "$(dirname "$0")/.."

if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found. Please run ./unix-macos/setup.sh first."
    exit 1
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

echo "[INFO] Starting Streamlit Application..."
python3 -m streamlit run src/app.py
