#!/bin/bash

sudo cp udev/99-ETL_Testing_GUI.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger