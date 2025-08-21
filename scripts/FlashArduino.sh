#!/bin/bash
# Arduino Uno Flash Script using PlatformIO
# Usage: source FlashArduino.sh

set -e

PROJECT_DIR="$HOME/ETL_Testing_GUI/drivers/Arduino/"

cd "$PROJECT_DIR"

# Check and install PlatformIO if needed
if ! command -v pio >/dev/null 2>&1; then
    echo "Installing PlatformIO..."
    curl -fsSL get-platformio.py https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py
    export PATH=$PATH:~/.platformio/penv/bin
fi

# Install dependencies
echo "Installing dependencies..."
pio pkg install 

# Build and upload
echo "Building and uploading..."
pio run --target upload

echo "Arduino programmed successfully!"