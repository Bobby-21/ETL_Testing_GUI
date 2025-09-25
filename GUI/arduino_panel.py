import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel, QSizePolicy
)
from pathlib import Path
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from panel import Panel
import threading
import serial
import time
from ETL_Testing_GUI.src.sensors import Sensors

MAIN_DIR = Path(__file__).parent.parent
WORKER_PATH = MAIN_DIR / "src" / "recorder.py"


class ArduinoPanel(Panel):
    def __init__(self, title="Arduino"):
        super().__init__(title)

        # ---------- styles: white text + green connect button ----------
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
            background-color: #22c55e;
            color: #ffffff;
        }
        QPushButton#greenButton:hover { background-color: #16a34a; }
        QPushButton#greenButton:pressed { background-color: #15803d; }
        """)

        # ---------- spacer row to avoid overlapping the title ----------
        top_pad = max(24, self.fontMetrics().height() + 8)
        self.subgrid.setRowMinimumHeight(0, top_pad)
        row0 = 1

        # ---------- form: connect/disconnect/status ----------
        from PyQt5.QtWidgets import QHBoxLayout, QFormLayout
        form = QFormLayout()

        self.recorder_stop_evt = None
        self.recording_thread = None
        self.arduino = None

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
        self.btn_connect.clicked.connect(start_recording)

        self.btn_disconnect = QPushButton("Disconnect")
        self.lbl_status = QLabel("Disconnected")

        connect_row = QHBoxLayout()
        connect_row.addWidget(self.btn_connect)
        connect_row.addWidget(self.btn_disconnect)
        connect_row.addWidget(self.lbl_status, 1, Qt.AlignLeft)

        # ---------- sensor/status labels ----------
        def make_label(text):
            lbl = QLabel(text)
            lbl.setFont(QFont("Arial", 18, QFont.Bold))
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

        # ---------- layout into subgrid ----------
        self.subgrid.addLayout(form,       row0 + 0, 0)
        self.subgrid.addLayout(connect_row,row0 + 1, 0)
        self.subgrid.addWidget(self.ambtemp_lbl,   row0 + 2, 0)
        self.subgrid.addWidget(self.rH_lbl,        row0 + 3, 0)
        self.subgrid.addWidget(self.dewpoint_lbl,  row0 + 4, 0)
        self.subgrid.addWidget(self.dhtstatus_lbl, row0 + 5, 0)
        self.subgrid.addWidget(self.door_lbl,      row0 + 6, 0)
        self.subgrid.addWidget(self.leak_lbl,      row0 + 7, 0)
        self.subgrid.addWidget(self.TC1_lbl,       row0 + 8, 0)
        self.subgrid.addWidget(self.TC1_fault_lbl, row0 + 9, 0)
        self.subgrid.addWidget(self.TC2_lbl,       row0 + 10, 0)
        self.subgrid.addWidget(self.TC2_fault_lbl, row0 + 11, 0)
        self.subgrid.setRowStretch(row0 + 11, 1)

        def start_recording(port="/dev/arduino", baud=115200, timeout=1.0, sample_time=1.0):
            self.recorder_stop_evt = threading.Event()

            self.arduino = Sensors(port, baud, timeout)
            try:
                self.arduino.connect()
            except serial.SerialException as e:
                print(f"Failed to connect: {e}")

            self.recorder_stop_evt.clear()
            self.recording_thread = threading.Thread(target=record, args=(self.arduino, sample_time, self.recorder_stop_evt), daemon=True)
            self.recording_thread.start()

        def stop_recording(self):
            self.stop_evt.set()
            if self.thread:
                self.thread.join(timeout=1)
            if self.arduino:
                self.arduino.close()


        def record(ard, sample_time, stop_evt):
            while not stop_evt.is_set():

                try:
                    ard.update_all()
                    data = ard.package()
                except Exception as e:
                    print(f"Recording Error: {e}")

                self.ambtemp_lbl.setText(f"Ambient Temp: {data['Ambient Temperature']:.1f}°C")
                self.rH_lbl.setText(f"Relative Humidity: {data['Relative Humidity']:.1f}%")
                self.dewpoint_lbl.setText(f"Dew Point: {data['Dewpoint']:.1f}°C")
                self.dhtstatus_lbl.setText(f"DHT Status: {'OK' if data['DHT Status'] else 'FAULT'}")
                self.door_lbl.setText(f"Door: {'OPEN' if data['Door Status'] else 'CLOSED'}")
                self.leak_lbl.setText(f"Leak: {'YES' if data['Leak Status'] else 'NO'}")
                self.TC1_lbl.setText(f"TC1 Temp: {data['TC Temperatures'][0]:.1f}°C")
                self.TC1_fault_lbl.setText(f"TC1 Faults: {', '.join(data['TC Faults'][0]) if data['TC Faults'][0] != ['OK'] else 'OK'}")
                self.TC2_lbl.setText(f"TC2 Temp: {data['TC Temperatures'][1]:.1f}°C")
                self.TC2_fault_lbl.setText(f"TC2 Faults: {', '.join(data['TC Faults'][1]) if data['TC Faults'][1] != ['OK'] else 'OK'}") 

                time.sleep(sample_time)

        