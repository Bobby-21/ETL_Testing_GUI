# ETL Testing GUI

This Python GUI facilitates coldbox testing of ETL detector modules.

## Requirements

### Hardware
- Recirculating chiller
- Dry air supply
- Arduino sensors
    - DHT22 temperature/humidity sensor
    - [Type-T thermocouple](https://a.co/d/5xr8zDA) (x2)
    - [Thermocouple SPI digital interface](https://www.playingwithfusion.com/productview.php?catid=1001&pdid=64)
- Xilinx KCU105 FPGA Board
- CAEN NDT1470 high-voltage power supply
- Low voltage power supply
- Coldbox (see coldbox setup below)

### Software
- OS: Ubuntu 20.04.1
- [Vivado 2021.1](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/vivado-design-tools/archive.html)


## Coldbox Setup

## Installation

### Note: Many steps require sudo privileges

The following instructions were adapted from [this original SOP](./ETL_test_stand_setup.md), which you should refer to if any step is unclear.

### Cloning the repo

To clone this repo, please run `git clone --recurse-submodules <repo url>`. First check that the submodule branch is on `origin/dev-RBFv2`. You can do this by running the following.

```bash
cd module_test_sw/
git branch
```

If it is not on `origin/dev-RBFv2`, then run `git checkout origin/dev-RBFv2` while in the submodule.

### Vivado installation

You can follow [this link](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/vivado-design-tools/archive.html) and navigate to the 2021.1 download. Either the linux self-extracting web installer or tar file should be fine. You will likely have to make an account on the AMD website to download either. For specific instructions for unpacking the tar file and managing the license, see the [original SOP](./ETL_test_stand_setup.md). 

### IPbus installation

To download the IPbus software, move to the `scripts/` directory and run `source setup_ipbus.sh`. This [SOP](./ETL_test_stand_setup.md) also gives the step-by-step instructions.

### General setup

Move to the `scripts/` directory and run `source setup_env.sh`. This does the following:
- Downloads uv, the python dependency manager, and sets up the python environment for the project
- Sets up the python path for Tamalero
- Adds Vivado to path if not already

### Flashing firmware

To 


## User's Guide

## Contact

This project was written by Bobby Vitale (bobby21@bu.edu) and Insung Hwang (insert email) at Boston University. Please feel free to reach out with questions or issues. 