# GUI/arduino_panel.py
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QPushButton, QLabel, QHBoxLayout, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont

from panel import Panel

# repo root / src on sys.path (kept from your original for safety)
MAIN_DIR = Path(__file__).parent.parent
src_dir = MAIN_DIR / "src"
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

# import the client (which wraps QProcess + worker)
from src.devices.arduino.client import ArduinoClient


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

        QPushButton#redButton {
            background-color: #ef4444;
            color: #ffffff;
        }
        QPushButton#redButton:hover  { background-color: #dc2626; }
        QPushButton#redButton:pressed{ background-color: #b91c1c; }
        """)

        # ---------- spacer row to avoid overlapping the title ----------
        top_pad = max(24, self.fontMetrics().height() + 8)
        self.subgrid.setRowMinimumHeight(0, top_pad)
        row0 = 1

        # ---------- form: connect/disconnect/status ----------
        form = QFormLayout()

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("redButton")
        self.btn_disconnect.setEnabled(False)

        self.lbl_status = QLabel("Disconnected")

        connect_row = QHBoxLayout()
        connect_row.addWidget(self.btn_connect)
        connect_row.addWidget(self.btn_disconnect)
        connect_row.addWidget(self.lbl_status, 1, Qt.AlignLeft)

        # ---------- sensor/status labels ----------
        def make_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setFont(QFont("Arial", 18, QFont.Bold))
            return lbl

        self.ambtemp_lbl    = make_label("Ambient Temp: --.-°C")
        self.rH_lbl         = make_label("Relative Humidity: --.-%")
        self.dewpoint_lbl   = make_label("Dew Point: --.-°C")
        self.dhtstatus_lbl  = make_label("DHT Status: --")
        self.door_lbl       = make_label("Door: --")
        self.leak_lbl       = make_label("Leak: --")
        self.TC1_lbl        = make_label("TC1 Temp: --.-°C")
        self.TC1_fault_lbl  = make_label("TC1 Faults: --")
        self.TC2_lbl        = make_label("TC2 Temp: --.-°C")
        self.TC2_fault_lbl  = make_label("TC2 Faults: --")

        # ---------- layout into subgrid ----------
        self.subgrid.addLayout(form,         row0 + 0, 0)
        self.subgrid.addLayout(connect_row,  row0 + 1, 0)
        self.subgrid.addWidget(self.ambtemp_lbl,    row0 + 2, 0)
        self.subgrid.addWidget(self.rH_lbl,         row0 + 3, 0)
        self.subgrid.addWidget(self.dewpoint_lbl,   row0 + 4, 0)
        self.subgrid.addWidget(self.dhtstatus_lbl,  row0 + 5, 0)
        self.subgrid.addWidget(self.door_lbl,       row0 + 6, 0)
        self.subgrid.addWidget(self.leak_lbl,       row0 + 7, 0)
        self.subgrid.addWidget(self.TC1_lbl,        row0 + 8, 0)
        self.subgrid.addWidget(self.TC1_fault_lbl,  row0 + 9, 0)
        self.subgrid.addWidget(self.TC2_lbl,        row0 + 10, 0)
        self.subgrid.addWidget(self.TC2_fault_lbl,  row0 + 11, 0)
        self.subgrid.setRowStretch(row0 + 11, 1)

        # ---------- config ----------
        self.port = "/dev/arduino"
        self.baud = 115200
        self.timeout = 1.0
        self.sample_time = 1.0

        # ---------- client (separate process owner) ----------
        self.client = ArduinoClient(self)
        self.client.connected.connect(self._on_connected)
        self.client.disconnected.connect(self._on_disconnected)
        self.client.data.connect(self._on_data)
        self.client.status.connect(lambda st: None)  # optional
        self.client.error.connect(self._on_error)
        # self.client.log.connect(print)  # uncomment to see raw worker logs

        # ---------- button wiring ----------
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)

    # ===================== slots =====================

    @pyqtSlot()
    def _on_connect_clicked(self):
        if self.client.isRunning():
            return
        self._set_busy(True, msg="Connecting…")
        self.client.start(
            port=self.port,
            baud=self.baud,
            timeout=self.timeout,
            sample_time=self.sample_time,
        )

    @pyqtSlot()
    def _on_disconnect_clicked(self):
        if not self.client.isRunning():
            return
        self._set_busy(True, msg="Disconnecting…")
        self.client.stop()

    # ---- client signals ----
    def _on_connected(self, port: str):
        self.lbl_status.setText(f"Connected ({port})")
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def _on_disconnected(self):
        self.lbl_status.setText("Disconnected")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    def _on_error(self, message: str):
        # keep it simple; you can route this to a log widget as needed
        self.lbl_status.setText(f"Error: {message}")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    # ---- incoming sensor data ----
    def _on_data(self, data: dict):
        """
        data schema comes from Sensors.package(), same keys you already used:
          'Ambient Temperature', 'Relative Humidity', 'Dewpoint',
          'DHT Status', 'Door Status', 'Leak Status',
          'TC Temperatures' -> list [t1, t2, ...]
          'TC Faults'       -> list of lists, e.g. [['OK'], ['OK']]
        """
        try:
            self.ambtemp_lbl.setText(f"Ambient Temp: {float(data['Ambient Temperature']):.1f}°C")
            self.rH_lbl.setText(f"Relative Humidity: {float(data['Relative Humidity']):.1f}%")
            self.dewpoint_lbl.setText(f"Dew Point: {float(data['Dewpoint']):.1f}°C")
            self.dhtstatus_lbl.setText(f"DHT Status: {'OK' if data['DHT Status'] else 'FAULT'}")
            self.door_lbl.setText(f"Door: {'OPEN' if data['Door Status'] else 'CLOSED'}")
            self.leak_lbl.setText(f"Leak: {'YES' if data['Leak Status'] else 'NO'}")

            tc_temps = data.get('TC Temperatures') or []
            tc_faults = data.get('TC Faults') or []

            t1 = float(tc_temps[0]) if len(tc_temps) >= 1 else float("nan")
            t2 = float(tc_temps[1]) if len(tc_temps) >= 2 else float("nan")
            f1_list = tc_faults[0] if len(tc_faults) >= 1 else ['--']
            f2_list = tc_faults[1] if len(tc_faults) >= 2 else ['--']

            self.TC1_lbl.setText(f"TC1 Temp: {t1:.1f}°C" if t1 == t1 else "TC1 Temp: --.-°C")
            self.TC2_lbl.setText(f"TC2 Temp: {t2:.1f}°C" if t2 == t2 else "TC2 Temp: --.-°C")

            f1 = ', '.join(f1_list) if f1_list != ['OK'] else 'OK'
            f2 = ', '.join(f2_list) if f2_list != ['OK'] else 'OK'
            self.TC1_fault_lbl.setText(f"TC1 Faults: {f1}")
            self.TC2_fault_lbl.setText(f"TC2 Faults: {f2}")

            # once data flows, clear "busy" if we were connecting
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
        except Exception as e:
            self._on_error(f"parse error: {e}")

    # ===================== helpers =====================

    def _set_busy(self, busy: bool, msg: str = ""):
        if msg:
            self.lbl_status.setText(msg)
        self.btn_connect.setEnabled(not busy)
        # allow disconnect during busy so user can cancel
        self.btn_disconnect.setEnabled(True if busy and self.client.isRunning() else False)
