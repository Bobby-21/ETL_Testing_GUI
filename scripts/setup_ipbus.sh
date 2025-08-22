#!/bin/bash

cd "$HOME"

set -e

echo "Updating..."
sudo apt update -y

echo "Upgrading..."
sudo apt upgrade -y

echo "Installing git and python3.8..."
sudo apt install -y git python3.8

echo "Installing packages for ipbus software..."
sudo apt-get install -y make erlang g++ libboost-all-dev libpugixml-dev python3-all-dev rsyslog

echo "Cloning ipbus repo"
git clone --depth=1 -b v2.8.3 --recurse-submodules https://github.com/ipbus/ipbus-software.git
cd ipbus-software

echo "Making"
sudo make PYTHON=python3
sudo make install PYTHON=python3