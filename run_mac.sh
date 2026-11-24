#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "[Setup] Creating Python virtual environment (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Ensure Homebrew adb is on PATH for Apple Silicon / Intel Macs
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "[Run] Starting Underdark Macro Solver..."
python3 main.py
