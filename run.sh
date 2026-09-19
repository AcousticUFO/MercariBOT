#!/usr/bin/env bash
# MercariBOT Launcher for Linux / macOS
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -e .
else
    source .venv/bin/activate
fi

python main.py "$@"
