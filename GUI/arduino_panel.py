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
src_dir = MAIN_DIR / "src"
sys.path.append(str(src_dir))

from sensors import Sensors


class ArduinoPanel(Panel):
    def __init__(self, title="Arduino"):
        super().__init__(title)

        self.setObjectName("arduinoPanel")
        self.setStyleSheet("""
        #arduinoPanel, #arduinoPanel QWidget { color: #ffffff; }
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

        self.recorder_stop_evt = None
        self.recording_thread = None

        self.log_status = False
        self.log_timestamp = None

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
        self.btn_connect.clicked.connect(self.start_recording)
        self.btn_connect.setEnabled(True)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("redButton")
        self.btn_disconnect.clicked.connect(self.stop_recording)
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

        self.ambtemp_lbl = make_label("Ambient Temp: --.-°C")
        self.rH_lbl = make_label("Relative Humidity: --.-%")
        self.dewpoint_lbl = make_label("Dew Point: --.-°C")
        self.dhtstatus_lbl = make_label("DHT Status: --")
        self.door_lbl = make_label("Door: --")
        self.leak_lbl = make_label("Leak: --")
        self.TC1_lbl = make_label("TC1 Temp: --.-°C")
        self.TC1_fault_lbl = make_label("TC1 Faults: --")
        self.TC2_lbl = make_label("TC2 Temp: --.-°C")
        self.TC2_fault_lbl = make_label("TC2 Faults: --")


        label_grid = QGridLayout()

        label_grid.addWidget(self.TC1_lbl, 0, 0)
        label_grid.addWidget(self.TC2_lbl, 1, 0)
        label_grid.addWidget(self.door_lbl, 2, 0)
        label_grid.addWidget(self.leak_lbl, 3, 0)
        label_grid.addWidget(self.TC1_fault_lbl, 4, 0)
        label_grid.addWidget(self.TC2_fault_lbl, 5, 0)

        label_grid.addWidget(self.ambtemp_lbl, 0, 1)
        label_grid.addWidget(self.rH_lbl, 1, 1)
        label_grid.addWidget(self.dewpoint_lbl, 2, 1)
        label_grid.addWidget(self.dhtstatus_lbl, 3, 1)


        label_grid.setColumnStretch(0, 1)
        label_grid.setColumnStretch(1, 1)

        buttons_and_labels = QVBoxLayout()
        buttons_and_labels.addLayout(button_row)
        buttons_and_labels.addLayout(label_grid)
        self.subgrid.addLayout(buttons_and_labels, 1, 0, 1, 2, alignment=Qt.AlignTop)
        self.arduino = Sensors("/dev/arduino", baudrate=115200, timeout=1.0)
        self.sample_time = 2.5

    def start_recording(self):
        if self.recording_thread != None:
            print("Recording thread already running")
            return
        
        self.recorder_stop_evt = threading.Event()
        try:
            self.arduino.connect()
            self.lbl_status.setText("Connected")
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")

        time.sleep(self.sample_time)
        self.recorder_stop_evt.clear()
        self.recording_thread = threading.Thread(target=self.record, daemon=True)
        self.recording_thread.start()
        self.btn_disconnect.setEnabled(True)
        self.btn_connect.setEnabled(False)

    def stop_recording(self):
        if self.recording_thread == None:
            print("Recording thread not running")
            return

        self.recorder_stop_evt.set()
        if self.recording_thread:
            self.recording_thread.join(timeout=1)
            self.recording_thread = None
        if self.arduino:
            self.arduino.close()
            self.lbl_status.setText("Disconnected")
            self.ambtemp_lbl.setText("Ambient Temp: --.-°C")
            self.rH_lbl.setText("Relative Humidity: --.-%")
            self.dewpoint_lbl.setText("Dew Point: --.-°C")
            self.dhtstatus_lbl.setText("DHT Status: --")
            self.door_lbl.setText("Door: --")
            self.leak_lbl.setText("Leak: --")
            self.TC1_lbl.setText("TC1 Temp: --.-°C")
            self.TC1_fault_lbl.setText("TC1 Faults: --")
            self.TC2_lbl.setText("TC2 Temp: --.-°C")
            self.TC2_fault_lbl.setText("TC2 Faults: --")
            self.btn_disconnect.setEnabled(False)
            self.btn_connect.setEnabled(True)



    def record(self):
        while not self.recorder_stop_evt.is_set():
            data = self.arduino.get_data()

            self.lbl_status.setText("Connected" if self.arduino.is_connected else "Disconnected")

            # DHT
            if self.arduino.ambtemp is not None:
                self.ambtemp_lbl.setText(f"Ambient Temp: {self.arduino.ambtemp}°C")
            else:
                self.ambtemp_lbl.setText(f"Ambient Temp: {self.arduino.ambtemp}")

            if self.arduino.rH is not None:
                self.rH_lbl.setText(f"Relative Humidity: {self.arduino.rH}%")
            else:
                self.rH_lbl.setText(f"Relative Humidity: {self.arduino.rH}")
            
            if self.arduino.rH is not None and self.arduino.ambtemp is not None:
                self.dewpoint_lbl.setText(f"Dew Point: {self.arduino.dewpoint}°C")
            else:
                self.dewpoint_lbl.setText(f"Dew Point: {self.arduino.dewpoint}")

            self.dhtstatus_lbl.setText(f"DHT Status: {'OK' if self.arduino.dhtstatus else 'FAULT'}")

            # Digital sensors
            self.door_lbl.setText(f"Door: {'OPEN' if self.arduino.door else 'CLOSED'}")
            self.leak_lbl.setText(f"Leak: {'OK' if self.arduino.leak else 'LEAKING'}")

            # Thermocouples
            if self.arduino.TCtemps[0] is not None:
                self.TC1_lbl.setText(f"TC1 Temp: {self.arduino.TCtemps[0]}°C")
            else:
                self.TC1_lbl.setText(f"TC1 Temp: {self.arduino.TCtemps[0]}")

            if self.arduino.TCfaults[0] == None:
                self.TC1_fault_lbl.setText(f"TC1 Faults: N/A")
            else:
                self.TC1_fault_lbl.setText(f"TC1 Faults: {', '.join(self.arduino.TCfaults[0]) if self.arduino.TCfaults[0] != 'No Faults' else 'No Faults'}")
            
            if self.arduino.TCtemps[1] is not None:
                self.TC2_lbl.setText(f"TC2 Temp: {self.arduino.TCtemps[1]}°C")
            else:
                self.TC2_lbl.setText(f"TC2 Temp: {self.arduino.TCtemps[1]}")

            if self.arduino.TCfaults[1] == None:
                self.TC2_fault_lbl.setText(f"TC2 Faults: N/A") 
            else:
                self.TC2_fault_lbl.setText(f"TC2 Faults: {', '.join(self.arduino.TCfaults[1]) if self.arduino.TCfaults[1] != 'No Faults' else 'No Faults'}") 

            if not self.arduino.dhtstatus:
                print("Restarting DHT")
                self.arduino.restart_dht()
                time.sleep(1)

            if self.log_status:
                timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
                maindir = Path(__file__).parent.parent

                resultdir = maindir / "Sensor Data"
                if not os.path.isdir(resultdir):
                    os.makedirs(resultdir)

                resultdir.mkdir(exist_ok=True)

                outfile = resultdir / f"sensor_data_{self.log_timestamp}.csv"
                with open(outfile, 'a') as f:
                    f.write(f"{timestamp}: {data}\n")
            time.sleep(self.sample_time)

    def toggle_log(self):
        self.log_status = not self.log_status
        if self.log_status:
            self.lbl_logging.setText("Logging")
            self.log_timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
        else:
            self.lbl_logging.setText("Not Logging")
