#!/bin/bash

# Get version from command line argument
version=${1:-"v3.2.3"}

# Check and install dependencies
for tool in curl jq wget unzip; do
    if ! command -v $tool >/dev/null 2>&1; then
        echo "Installing $tool..."
        sudo apt install -y $tool
    fi
done

# Function to add to .bashrc
function_to_add='get_firmware_zip() {
    version=$1
    project="etl_test_fw"
    projectid="107856"
    file=$project-$version.zip
    url=$(curl  "https://gitlab.cern.ch/api/v4/projects/${projectid}/releases/$version" | jq '\''.description'\'' | sed -n "s|.*\[$project.zip\](\(.*\)).*|\1|p")
    wget $url
    unzip $file
}'

# Check if function already exists in .bashrc
if grep -q "get_firmware_zip()" ~/.bashrc; then
    echo "Function 'get_firmware_zip' already exists in ~/.bashrc"
    echo "Skipping addition to avoid duplicates."
else
    echo "Adding 'get_firmware_zip' function to ~/.bashrc..."
    echo "" >> ~/.bashrc
    echo "# Get firmware zip function" >> ~/.bashrc
    echo "$function_to_add" >> ~/.bashrc
    echo "Function added successfully!"
fi

source ~/.bashrc

cd "$HOME/ETL_Testing_GUI/drivers/KCU/"

# Check if firmware folder already exists
firmware_folder="etl_test_fw-$version"
if [ -d "$firmware_folder" ]; then
    echo "Firmware folder '$firmware_folder' already exists. Skipping download."
else
    echo "Downloading firmware version: $version"
    get_firmware_zip $version
fi