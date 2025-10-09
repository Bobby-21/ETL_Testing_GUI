#!/bin/bash

cp ../udev/99-ETL_Testing.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger