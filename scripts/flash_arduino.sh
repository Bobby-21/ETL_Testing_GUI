#!/bin/bash
# Arduino Uno Flash Script using PlatformIO
# Usage: source FlashArduino.sh

set -e

CURR_DIR="$PWD"
PROJECT_DIR="$HOME/ETL_Testing_GUI/drivers/Arduino/"

cd "$PROJECT_DIR"

# Check and install pip if needed
if ! command -v pip >/dev/null 2>&1; then
    echo "Installing pip..."
    sudo apt install -y pip
fi

# Check and install PlatformIO if needed
if ! command -v pio >/dev/null 2>&1; then
    echo "Installing PlatformIO..."
    python3 -m pip install -U platformio
    export PATH=$PATH:~/.local/bin
fi

# Install dependencies
echo "Installing dependencies..."
pio pkg install 

# Build and upload
echo "Building and uploading..."
pio run --target upload

echo "Arduino programmed successfully!"
cd "$CURR_DIR"