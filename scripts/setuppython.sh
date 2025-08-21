#!/bin/bash

# Python Project Setup Script using uv sync
# Usage: source setup.sh

echo "Setting up Python project with uv..."

# Check and install curl if needed
if ! command -v curl >/dev/null 2>&1; then
    echo "Installing curl..."
    sudo apt install curl
fi

# Check and install uv if needed
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Use uv sync to create venv and install dependencies in one step
echo "Syncing project dependencies..."
uv sync

# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

echo "Setup complete! Virtual environment is activated."
echo "To deactivate later, run: deactivate"