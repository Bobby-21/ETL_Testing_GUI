# ETL:200 - ETL Test Stand Setup
Author: Ian Reed
Last Edited: May 24, 2023

## Abstract
   This SOP covers the procedure of installing all parts of the ETL Test stand.


# Prep
You will need to be using Ubuntu 20.04 LTS, or a RHEL based distro. Newer Ubuntu versions have trouble with the IPBUS software compilation.

Additional information about the process may be found at these links

https://etl-rb.docs.cern.ch/Hardware/ 

https://docs.xilinx.com/r/en-US/ug973-vivado-release-notes-install-license/Download-and-Installation

While this step is not needed to install Vivado, if these are not in the system, the module test software won't work.
It is better to do them now, as OS refershes/changes were needed to diagnose this problem and avoiding having to download Vivado several times is in your best interest.

First, update the system and install git and python

```
sudo apt update
sudo apt upgrade
sudo apt install git
sudo apt install python3.8
```

THe update step might do the python3.8, but this is fine.

Next, install the packages needed to compile the ipbus software

```sudo apt-get install -y make erlang g++ libboost-all-dev libpugixml-dev python-all-dev rsyslog```

with the needed packages ready, download, compile, and install ipbus
```
git clone --depth=1 -b v2.8.3 --recurse-submodules https://github.com/ipbus/ipbus-software.git
cd ipbus-software
sudo make PYTHON=python3
sudo make install PYTHON=python3
```
With this finished, check that the install worked. Use the first command to temporarily set the ipbus path, then open a session of python and import uhal
```
export LD_LIBRARY_PATH=/opt/cactus/lib:$LD_LIBRARY_PATH
python3
import uhal
```
If there are no errors while importing, everthing worked and you can continue the installation process.

# Vivado Installation
Use the Batch Mode Installation Flow, outlined in this pdf starting on page 47:

https://docs.xilinx.com/v/u/2019.2-English/ug973-vivado-release-notes-install-license

This is a terminal based, which is more reliable than the GUI version.

You will likely need to install this package
```sudo apt install libtinfo5```
otherwise the installation will not complete, hanging on the finishing stage.

Navigate here:
https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/vivado-design-tools/2021-1.html

We want the 2021.1 version of the package. Of the 3 options, select

```Xilinx Unified Installer 2021.1 SFD (TAR)```

a tar file that contains the programs we want to use. The file is rather large and can take some time to download depending on network speeds. Unpack it with the command:

```tar -xvf Xilinx_Unified_2021.1_0610_2318.tar.gz```


With the file unpacked, navigate to the new directory. First, make a install config file with
```./xsetup -b ConfigGen```
and follow the prompts on the terminal to create the file. Select Vivado(option 2) if you want to be able to edit code, or Lab Edition (option 5) if you just want to upload firmware. In the case of a Vivado installation, you will need a software key from the lab manager. Make sure to select the Enterprise version of Vivado, otherwise you will not be able to program the board.

The script will tell you the location of the newly created config file. You can open the file to make changes, but the defaults should be fine. With the config file ready, use this command to begin the install process
```./xsetup --agree XilinxEULA,3rdPartyEULA,WebTalkTerms --batch Install --config <path/to/config>```
Installation shouldn't take too long, O(30min). This process may be repeated if different Vivado versions need to be installed, just rerun the config creation command with different options to get the relevant config files.

For the following script to work, make sure to add the path to Vivado to you $PATH. You can do so by adding 
```export PATH="/tools/Xilinx/Vivado/2021.1/bin/:$PATH"```
to your .bashrc file. You can get the specific path from the desktop icon created when installing Vivado

# Vivado Software Key Management

### WARNING: WE ONLY HAVE ONE KEY FOR NOW. CONTACT THE LAB MANAGER TO DETERMINE IF A NEW KEY IS NEEDED. IF YOU USE THE EXISTING KEY, THE PREVIOUS INSTALL OF VIVADO WILL BREAK

Start by oppening Vivado. Once it is running, open the Help tab at the top, and navigate to Manage License. This will open the Vivado License Manager program.

Navigate to the ```View System Information->View Host Infromation``` page. You will need this info modify the key.
Open the license managment website through the ```Get License->Obtain License``` tabs. Click Connect Now to be taken to the webpage.

From the webpage, navigate to the ```Manage Licenses``` tab. Scroll down and click ```Modify License```. Enter the information from the ```View Host``` metioned earlier. Click through the prompts until a window appears telling you a new key has been sent to the lab manager.

Get this file and move it to the ```$HOME/.Xilinx``` directory.

Back in the Vivado License Manager, navigate to ```Manage License->View License Status```. Click refresh and the keys should appear.

# KCU Communication Settings
First, install the Vivado cable drivers

```
cd ${vivado_install_dir}/data/xicom/cable_drivers/lin64/install_script/install_drivers/
./install_drivers
```
Next, set the  clock for the board. Use
```screen /dev/ttyUSB0 115200```
to make the connecting. If the menu does not show, press space
From the menu select ```1. Set Programmable Clocks```
followed by ```1. Set KCU105 Si570 User Clock Frequency```
with a value of ```320.64MHz```
Save (3)->(1)->(0)

Check the clock value with ```5. View KCU105 Saved Clocks in EEPROM```

We want these setting to survive power cycling the board, so go to ```6. Set KCU105 Clock Restore Options```
Select option (2)
Return to Clock Menu (0)

To exit the screen session, ```crtl-k```

Next, configure the ethernet to be able to communicate with the board. This is needed for the module test software.
Open your network settings, naviate to the IPv4 tab of the ethernet port connected to the KCU, switch to 'Manual'
Set the address to ```192.168.0.XXX``` and Netmask to ```255.255.0.0```
XXX can be any value not already taken on the network. For simple setups with only the KCU and no other hardware ```20``` is a good default value


# Loading Firmware
To upload firmware to the KCU105, first add this command to your .bashrc
```
get_firmware_zip() {
    version=$1
    project="etl_test_fw"
    projectid="107856"
    file=$project-$version.zip
    url=$(curl  "https://gitlab.cern.ch/api/v4/projects/${projectid}/releases/$version" | jq '.description' | sed -n "s|.*\[$project.zip\](\(.*\)).*|\1|p")
    wget $url
    unzip $file
}
```
To activate either close and reopen the terminal, or run ```source .bashrc``` from your home directory.

You may need to install ```curl``` and ```jq``` for the script to work.
Run the scrip with the version of firmware you want to use

```get_firmware_zip v2.1.8```

Move to the directory that has been created, something like ```etl_test_fw-v2.1.8```
With the board connected and powered on, running ```source program.sh``` will load the firmware to the board. The self test LEDs should now either start "breathing" or "cyloning" to indicate the firmware is loaded.

# Module Test Software
This guided is a modified version of this guided
https://etl-rb.docs.cern.ch/Software/module-test/
Please check here for more details

```git clone https://gitlab.cern.ch/cms-etl-electronics/module_test_sw.git```

Further instrucions on running the software can be found at the github on the software
