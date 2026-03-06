#!/bin/bash

# Switch to the project root directory
cd "$(dirname "$0")/.."

echo "==================================================="
echo "     llms.txt Generator - Unix/macOS Setup Script"
echo "==================================================="

# Function to text command existence
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Find Python 3
PYTHON_CMD="python3"
if ! command_exists $PYTHON_CMD; then
  # Fallback to python if python3 isn't named specifically but is Python 3
  if command_exists python && python -c 'import sys; exit(0) if sys.version_info >= (3, 8) else exit(1)' >/dev/null 2>&1; then
      PYTHON_CMD="python"
  else
    echo "[ERROR] Python 3.8+ is not installed or not in your PATH."
    echo ""
    echo "Linux Installation:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-venv"
    echo "  Fedora: sudo dnf install python3"
    echo ""
    echo "macOS Installation:"
    echo "  Homebrew: brew install python3"
    echo "  Or download from: https://www.python.org/downloads/macos/"
    echo ""
    exit 1
  fi
fi

$PYTHON_CMD -c "import sys; print(f'[OK] Found Python {sys.version_info.major}.{sys.version_info.minor}')"

# Create virtual environment
if [ ! -f "venv/bin/activate" ]; then
    echo "[INFO] Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        echo "Note: On Ubuntu/Debian you might need to run: sudo apt install python3-venv"
        exit 1
    fi
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists."
fi

# Activate and install requirements
echo "[INFO] Activating virtual environment and installing dependencies..."
source venv/bin/activate

pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies."
        exit 1
    fi
    echo "[OK] Dependencies installed successfully."
else
    echo "[WARNING] requirements.txt not found."
fi

echo "[INFO] Installing Playwright Chromium browser..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install Playwright browser. Run 'playwright install chromium' manually."
    exit 1
fi
echo "[OK] Playwright Chromium installed."

echo "==================================================="
echo "Setup Complete!"
echo ""
echo "To start the application, run:"
echo "   ./unix-macos/run.sh"
echo "==================================================="
