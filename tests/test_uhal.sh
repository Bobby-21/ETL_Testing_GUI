#!/bin/bash

echo "Testing uHAL install"

export LD_LIBRARY_PATH=/opt/cactus/lib:$LD_LIBRARY_PATH

if python3 -c "import uhal"; then
    echo "uHAL insalled succesfully"
else
    echo "uHAL install failed"
fi