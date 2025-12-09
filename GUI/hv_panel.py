import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel, QSizePolicy, QLineEdit, QHBoxLayout, QFormLayout, QVBoxLayout
)
from pathlib import Path
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from panel import Panel
import threading
import serial
import time
import os

MAIN_DIR = Path(__file__).parent.parent
hv_dir = MAIN_DIR / "drivers" / "HV"
sys.path.append(str(hv_dir))

from HVPowerSupply import HVPowerSupply

class HVPanel(Panel):
    def __init__(self, title="HV Supply"):
        super().__init__(title)

        self.setObjectName("HVPanel")
        self.setStyleSheet("""
        #HVPanel QWidget { color: #ffffff; }
        QLabel { color: #ffffff; }

        QLineEdit, QPlainTextEdit {
            color: #ffffff;
            border: 1px solid #ffffff;
            border-radius: 6px;
            padding: 4px 6px;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
        }

        QPushButton {
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 8px 14px;
            font-weight: 600;
        }
        QPushButton:disabled { color: #9aa5b1; }

        QPushButton#greenButton {
            background-color: #16a34a;
            color: #ffffff;
        }
        QPushButton#greenButton:hover { background-color: #22c55e; }
        QPushButton#greenButton:pressed { background-color: #15803d; }
        QPushButton#greenButton:disabled { background-color: #14532d; color: #9aa5b1;}


        QPushButton#redButton {
            background-color: #e53935;
            color: #ffffff;
        }
        QPushButton#redButton:hover { background-color: #ef5350; }
        QPushButton#redButton:pressed { background-color: #c62828; }
        QPushButton#redButton:disabled { background-color: #7f1d1d; color: #9aa5b1;}
                           
        QPushButton#blueButton {
            background-color: #007bff;
            color: #ffffff;
        }
        QPushButton#blueButton:hover { background-color: #339cff; }
        QPushButton#blueButton:pressed { background-color: #0056b3; }
        """)

        self.hv_stop_evt = None
        self.hv_thread = None
        self.log_status = False
        self.log_timestamp = None

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
        self.btn_connect.clicked.connect(self.start_hv)
        self.btn_connect.setEnabled(True)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("redButton")
        self.btn_disconnect.clicked.connect(self.stop_hv)
        self.btn_disconnect.setEnabled(False)

        self.lbl_status = QLabel("Disconnected")

        self.btn_logging = QPushButton("Toggle Logging")
        self.btn_logging.setObjectName("blueButton")
        self.btn_logging.clicked.connect(self.toggle_log)
        self.lbl_logging = QLabel("Not Logging")

        button_row = QHBoxLayout()
        button_row.addWidget(self.btn_connect)
        button_row.addWidget(self.btn_disconnect)
        button_row.addWidget(self.lbl_status, 1, Qt.AlignLeft)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_logging)
        button_row.addWidget(self.lbl_logging, 1, Qt.AlignLeft)

        def make_label(text):
            lbl = QLabel(text)
            lbl.setFont(QFont("Calibri", 15))
            return lbl
        
        channel_row = QHBoxLayout()
        self.lbl_channel = make_label("Channel: ---")
        channel_row.addWidget(self.lbl_channel)

        set_label_row = QHBoxLayout()
        self.lbl_set_voltage = make_label("VSET: --- V")
        self.lbl_set_current = make_label("ISET: ---.- uA")
        set_label_row.addWidget(self.lbl_set_voltage)
        set_label_row.addWidget(self.lbl_set_current)

        mon_label_row = QHBoxLayout()
        self.lbl_mon_voltage = make_label("VMON: --- V")
        self.lbl_mon_current = make_label("IMON: ---.- uA")
        mon_label_row.addWidget(self.lbl_mon_voltage)
        mon_label_row.addWidget(self.lbl_mon_current)

        input_row = QHBoxLayout()

        channel_input_row = QHBoxLayout()
        voltage_input_row = QHBoxLayout()
        current_input_row = QHBoxLayout()

        self.btn_channel_on = QPushButton("Channel ON")
        self.btn_channel_off = QPushButton("Channel OFF")
        self.btn_channel_on.setObjectName("greenButton")
        self.btn_channel_off.setObjectName("redButton")
        self.btn_channel_on.clicked.connect(self.set_channel)
        self.btn_channel_off.clicked.connect(self.set_channel)
        channel_input_row.addWidget(self.btn_channel_on)
        channel_input_row.addWidget(self.btn_channel_off)

        self.lbl_set_voltage_field = make_label("Set Voltage (V): ")
        self.set_voltage_field = QLineEdit(parent=self)
        self.set_voltage_field.setFixedSize(60,30)
        self.btn_vset = QPushButton("Set")
        self.btn_vset.setObjectName("blueButton")
        self.btn_vset.clicked.connect(self.set_voltage)

        self.lbl_set_current_field = make_label("Set Current Limit (uA):" )
        self.set_current_field = QLineEdit(parent=self)
        self.set_current_field.setFixedSize(60,30)
        self.btn_iset = QPushButton("Set")
        self.btn_iset.setObjectName("blueButton")
        self.btn_iset.clicked.connect(self.set_current)


        voltage_input_row.addWidget(self.lbl_set_voltage_field)
        voltage_input_row.addWidget(self.set_voltage_field)
        voltage_input_row.addWidget(self.btn_vset)
        current_input_row.addWidget(self.lbl_set_current_field)
        current_input_row.addWidget(self.set_current_field)
        current_input_row.addWidget(self.btn_iset)

        
        input_row.addLayout(channel_input_row)
        input_row.addStretch(1)
        input_row.addLayout(voltage_input_row)
        input_row.addStretch(1)
        input_row.addLayout(current_input_row)
        input_row.addStretch(1)


        main_layout = QVBoxLayout()
        main_layout.addLayout(button_row)
        main_layout.addLayout(channel_row)
        main_layout.addLayout(set_label_row)
        main_layout.addLayout(mon_label_row)
        main_layout.addLayout(input_row)



        self.subgrid.addLayout(main_layout, 1, 0, 5, 5, Qt.AlignTop)
        self.sample_time = 0.5
        self.cmd_waiting = False
        self.cmd = None



    def start_hv(self):
        if self.hv_thread != None:
            print("HV thread already running")
            return
        
        self.hv_stop_evt = threading.Event()
        try:
            # TODO: Add more channels
            self.hv = HVPowerSupply("/dev/hv_supply", baud=9600, bd_addr=0, channel=0)
            self.lbl_status.setText("Connected")
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
        
        self.hv_stop_evt.clear()
        self.hv_thread = threading.Thread(target=self.hv_run, daemon=True)
        self.hv_thread.start()
        self.btn_disconnect.setEnabled(True)
        self.btn_connect.setEnabled(False)
        time.sleep(self.sample_time)
   
    def stop_hv(self):
        if self.hv_thread == None:
            print("HV thread not running")
            return
        
        self.hv_stop_evt.set()
        if self.hv_thread:
            self.hv_thread.join()
            self.hv_thread = None
        if self.hv:
            self.hv.close()
            self.lbl_status.setText("Disconnected")
            self.lbl_set_voltage.setText("VSET: --- V")
            self.lbl_set_current.setText("ISET: ---.- uA")
            self.lbl_mon_voltage.setText("VMON: --- V")
            self.lbl_mon_current.setText("IMON: ---.- uA")
            self.lbl_channel.setText("Channel: ---")
            self.btn_disconnect.setEnabled(False)
            self.btn_connect.setEnabled(True)


    def hv_run(self):
        while not self.hv_stop_evt.is_set():
            if not self.cmd_waiting:
                self.vset = self.hv.extract_float_value(self.hv.read_vset())
                self.vmon = self.hv.extract_float_value(self.hv.read_vmon())
                self.iset = self.hv.extract_float_value(self.hv.read_iset())
                self.imon = self.hv.extract_float_value(self.hv.read_imon())
                self.status = int(self.hv.read_status()['VAL'])
                self.channel = self.status & 1

                if self.channel:
                    self.lbl_channel.setText("Channel: ON")
                    self.btn_channel_off.setEnabled(True)
                    self.btn_channel_on.setEnabled(False)
                else:
                    self.lbl_channel.setText("Channel: OFF")
                    self.btn_channel_off.setEnabled(False)
                    self.btn_channel_on.setEnabled(True)

                self.lbl_set_voltage.setText(f"VSET: {self.vset} V")
                self.lbl_set_current.setText(f"ISET: {self.iset} uA")
                self.lbl_mon_voltage.setText(f"VMON: {self.vmon} V")
                self.lbl_mon_current.setText(f"IMON: {self.imon} uA")
                if self.log_status:
                    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
                    maindir = Path(__file__).parent.parent

                    resultdir = maindir / "Environmental Data" / "HV Supply Data"
                    if not os.path.isdir(resultdir):
                        os.makedirs(resultdir)

                    resultdir.mkdir(exist_ok=True)

                    outfile = resultdir / f"hv_supply_data_{self.log_timestamp}.csv"

                    data = {"Channel": self.channel, "VSET": self.vset, "VMON": self.vmon, "ISET": self.iset, "IMON": self.imon, "Status": self.status}
                    with open(outfile, 'a') as f:
                        f.write(f"{timestamp}: {data}\n")
            else:
                if self.cmd == "vset":
                    try:
                        value = float(self.set_voltage_field.text())
                        self.hv.set_voltage(value)
                    except Exception as e:
                        print(f"Error: {e}")
                        self.set_voltage_field.clear()
                    self.set_voltage_field.clear()
                
                elif self.cmd == "iset":
                    try:
                        value = float(self.set_current_field.text())
                        self.hv.set_current_limit(value)
                    except Exception as e:
                        print(f"Error: {e}")
                        self.set_current_field.clear()
                    self.set_current_field.clear()

                elif self.cmd == "channel":
                    if self.channel:
                        self.hv.set_channel_off()
                    else:
                        self.hv.set_channel_on()
                
                
                self.cmd_waiting = False
                self.cmd = None
            time.sleep(self.sample_time)

    def set_voltage(self):
        self.cmd_waiting = True
        self.cmd = "vset"

    def set_current(self):
        self.cmd_waiting = True
        self.cmd = "iset"
    
    def set_channel(self):
        self.cmd_waiting = True
        self.cmd = "channel"

    def toggle_log(self):
        self.log_status = not self.log_status
        if self.log_status:
            self.lbl_logging.setText("Logging")
            self.log_timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
        else:
            self.lbl_logging.setText("Not Logging")