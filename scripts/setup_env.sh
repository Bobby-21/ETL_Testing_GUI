#!/bin/bash

# Python Project Setup Script using uv sync
# Usage: source setup.sh

echo "Setting up Python project with uv..."

# Check and install curl if needed
if ! command -v curl >/dev/null 2>&1; then
    echo "Installing curl..."
    sudo apt install -y curl
fi

# Check and install uv if needed
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -fsSL https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi


# Setup paths for tamalero
cd "$HOME/ETL_Testing_GUI/"
source "module_test_sw/setup.sh"
cd "module_test_sw/"
source "module_test_sw/setup.sh"
cd ".."

# Recreate uv env with system-site-packages so uHAL becomes visible to env
rm -rf .venv
python3.8 -m venv .venv --system-site-packages
uv python pin 3.8

# Use uv sync to create venv and install dependencies in one step
echo "Syncing project dependencies..."
uv sync