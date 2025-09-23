import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel, QSizePolicy
)
from pathlib import Path
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from panel import Panel

MAIN_DIR = Path(__file__).parent.parent
WORKER_PATH = MAIN_DIR / "src" / "sensors.py"

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

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
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

        self.ambtemp_lbl = make_label("Ambient Temp: 24.2°C")
        self.rH_lbl = make_label("Relative Humidity: 45.3%")
        self.dewpoint_lbl = make_label("Dew Point: 12.3°C")
        self.dhtstatus_lbl = make_label("DHT Status: OK")
        self.door_lbl = make_label("Door: Closed")
        self.leak_lbl = make_label("Leak: No Leak")
        self.TC1_lbl = make_label("TC1 Temp: 22.5°C")
        self.TC1_fault_lbl = make_label("TC1 Faults: OK")
        self.TC2_lbl = make_label("TC2 Temp: 23.1°C")
        self.TC2_fault_lbl = make_label("TC2 Faults: OK")

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