#!/bin/bash

# Switch to the project root directory
cd "$(dirname "$0")/.."

echo "==================================================="
echo "   llms.txt Generator - Unix/macOS Teardown Script"
echo "==================================================="
echo ""
echo "WARNING: This will completely remove:"
echo " 1. The Python virtual environment (venv)"
echo " 2. Any saved progress (state.json)"
echo " 3. Any generated llms.txt files"
echo ""

read -p "Are you sure you want to continue? (Y/N): " choice
case "$choice" in 
  y|Y ) echo "";;
  * ) echo "[INFO] Teardown cancelled."; exit 0;;
esac

echo "[INFO] Starting teardown..."

# Remove venv directory
if [ -d "venv" ]; then
    echo "[1/3] Removing virtual environment..."
    rm -rf venv
    echo "[OK] Virtual environment removed."
else
    echo "[1/3] Virtual environment not found, skipping."
fi

# Remove state file
if [ -f "state.json" ]; then
    echo "[2/3] Removing state.json..."
    rm state.json
    echo "[OK] State removed."
else
    echo "[2/3] State file not found, skipping."
fi

# Remove generated files
if [ -f "llms.txt" ]; then
    echo "[3/3] Removing generated llms.txt..."
    rm llms.txt
    echo "[OK] Generated llms.txt removed."
else
    echo "[3/3] llms.txt not found, skipping."
fi

echo ""
echo "==================================================="
echo "Teardown Complete!"
echo "You can now run ./unix-macos/setup.sh again from a clean slate."
echo "==================================================="
