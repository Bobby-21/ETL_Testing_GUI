import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel, QSizePolicy, QHBoxLayout, QFormLayout, QVBoxLayout
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
        #arduinoPanel, #HVPanel QWidget { color: #ffffff; }
        QLabel { color: #ffffff; }

        QLineEdit, QPlainTextEdit {
            color: #ffffff;
            border: 1px solid #374151;
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
        button_row.addStretch(2)
        button_row.addWidget(self.btn_logging)
        button_row.addWidget(self.lbl_logging, 1, Qt.AlignLeft)

        def make_label(text):
            lbl = QLabel(text)
            lbl.setFont(QFont("Calibri", 15, QFont.Bold))
            return lbl
        
        set_label_row = QHBoxLayout()
        self.lbl_set_voltage = make_label("Set Voltage (V): --- V")
        self.lbl_set_current = make_label("Set Current Limit (uA): ---.- uA")
        set_label_row.addWidget(self.lbl_set_voltage)
        set_label_row.addWidget(self.lbl_set_current)

        mon_label_row = QHBoxLayout()
        self.lbl_mon_voltage = make_label("Mon Voltage (V): --- V")
        self.lbl_mon_current = make_label("Mon Current (uA): ---.- uA")
        mon_label_row.addWidget(self.lbl_mon_voltage)
        mon_label_row.addWidget(self.lbl_mon_current)

        main_layout = QVBoxLayout()
        main_layout.addLayout(button_row)
        main_layout.addLayout(set_label_row)
        main_layout.addLayout(mon_label_row)



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


    def stop_hv(self):
        if self.hv_thread == None:
            print("HV thread not running")
            return
        
        self.hv_stop_evt.set()
        self.hv_thread.join()
        self.hv_thread = None
        self.hv.close()
        self.lbl_status.setText("Disconnected")