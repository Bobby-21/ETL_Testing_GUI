import sys
# chiller_panel.py
import os
from PyQt5.QtWidgets import (
    QHBoxLayout, QFormLayout, QPushButton, QLabel,
    QLineEdit, QPlainTextEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QRegularExpression
from PyQt5.QtGui import QFont, QRegularExpressionValidator
from panel import Panel


class ChillerPanel(Panel):
    """
    Chiller control panel template.

    UI:
      - /dev device path input (e.g. /dev/ttyUSB0)
      - Connect/Disconnect (green) + status label
      - Temperature setpoint input + 'Set Temp' button
      - Local log view

    Integration:
      - Replace the stubs in _connect_device() and _send_setpoint()
        with your real protocol (serial/USB/Ethernet).
      - If pyserial is installed, the template will try to use it.
    """

    def __init__(self, title="Chiller"):
        super().__init__(title)

        # ---------- styles: white text + green connect button (no bg override) ----------
        self.setObjectName("chillerPanel")
        self.setStyleSheet("""
        #chillerPanel, #chillerPanel QWidget { color: #ffffff; }
        QLabel { color: #ffffff; }

        QLineEdit, QPlainTextEdit {
            color: #ffffff;
            border: 1px solid #374151;
            border-radius: 6px;
            padding: 4px 6px;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
        }

        /* Default buttons */
        QPushButton {
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 8px 14px;
            font-weight: 600;
        }
        QPushButton:disabled { color: #9aa5b1; }

        /* Green Connect button */
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
        row0 = 1  # start placing content from this row

        # ---------- form: /dev + connect ----------
        form = QFormLayout()

        self.dev_edit = QLineEdit()
        self.dev_edit.setPlaceholderText("/dev/ttyUSB0")
        dev_re = QRegularExpression(r"^/dev/.+")
        self.dev_edit.setValidator(QRegularExpressionValidator(dev_re))
        form.addRow("Device:", self.dev_edit)

        connect_row = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
        self.lbl_status = QLabel("Disconnected")
        connect_row.addWidget(self.btn_connect)
        connect_row.addWidget(self.lbl_status, 1, Qt.AlignLeft)

        # ---------- temperature controls ----------
        temp_row = QHBoxLayout()
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setDecimals(2)
        self.temp_spin.setSingleStep(0.10)
        self.temp_spin.setRange(-20.0, 120.0)  # adjust to your chiller
        self.temp_spin.setValue(25.00)
        self.temp_spin.setSuffix(" °C")

        self.btn_set = QPushButton("Set Temp")
        self.btn_set.setEnabled(False)  # disabled until connected

        temp_row.addWidget(QLabel("Setpoint:"))
        temp_row.addWidget(self.temp_spin)
        temp_row.addWidget(self.btn_set)

        # ---------- info: current temp and status ----------
        info_row = QHBoxLayout()
        self.lbl_current_temp = QLabel("Current Temp: -- °C")
        self.lbl_current_temp.setFont(QFont("Arial", 16, QFont.Bold))
        self.lbl_status_onoff = QLabel("Status: OFF")
        self.lbl_status_onoff.setFont(QFont("Arial", 16, QFont.Bold))
        info_row.addWidget(self.lbl_current_temp)
        info_row.addWidget(self.lbl_status_onoff)

        # ---------- local log ----------
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.Monospace)
        self.log.setFont(mono)
        self.log.setPlaceholderText("Chiller logs…")

        # ---------- layout into subgrid ----------
        self.subgrid.addLayout(form,       row0 + 0, 0)
        self.subgrid.addLayout(connect_row,row0 + 1, 0)
        self.subgrid.addLayout(temp_row,   row0 + 2, 0)
        self.subgrid.addLayout(info_row,   row0 + 3, 0)
        self.subgrid.addWidget(self.log,   row0 + 4, 0)
        self.subgrid.setRowStretch(row0 + 4, 1)

        # ---------- state ----------
        self._connected = False
        self._serial = None
        try:
            import serial  # optional
            self._serial_lib = serial
        except Exception:
            self._serial_lib = None

        # optional polling timer for status reads; keep stopped by default
        self._poll = QTimer(self)
        self._poll.setInterval(1000)
        self._poll.timeout.connect(self._poll_status)

        # ---------- signals ----------
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.btn_set.clicked.connect(self._on_set_clicked)

    # ===================== utils =====================

    def _append_log(self, text: str):
        self.log.appendPlainText(text.rstrip("\n"))
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _set_connected_ui(self, ok: bool):
        self._connected = ok
        self.lbl_status.setText("Connected" if ok else "Disconnected")
        self.btn_connect.setText("Disconnect" if ok else "Connect")
        self.btn_set.setEnabled(ok)

    # ===================== actions =====================

    @pyqtSlot()
    def _on_connect_clicked(self):
        if self._connected:
            self._append_log("[Chiller] Disconnecting…")
            self._disconnect_device()
            self._set_connected_ui(False)
            self._poll.stop()
            self._append_log("[Chiller] Disconnected.")
            return

        dev = self.dev_edit.text().strip()
        if not dev or not self.dev_edit.hasAcceptableInput():
            self._append_log("[Chiller] Please enter a valid /dev path (e.g. /dev/ttyUSB0).")
            return
        if not os.path.exists(dev):
            self._append_log(f"[Chiller] Warning: device path does not exist: {dev}")

        ok = self._connect_device(dev)
        if ok:
            self._set_connected_ui(True)
            self._append_log(f"[Chiller] Connected to {dev}.")
            # self._poll.start()  # uncomment if you implement periodic reads
        else:
            self._append_log("[Chiller] Connection failed.")

    @pyqtSlot()
    def _on_set_clicked(self):
        if not self._connected:
            self._append_log("[Chiller] Not connected.")
            return
        sp = float(self.temp_spin.value())
        self._append_log(f"[Chiller] Setting setpoint to {sp:.2f} °C …")
        ok = self._send_setpoint(sp)
        if ok:
            self._append_log("[Chiller] Setpoint command sent.")
        else:
            self._append_log("[Chiller] Failed to send setpoint.")

    # ===================== stubs you should replace =====================

    def _connect_device(self, dev_path: str) -> bool:
        """
        Replace this with your real connect logic. If pyserial is available,
        this will attempt to open the port at 9600-8N1 by default.
        """
        if self._serial_lib:
            try:
                self._serial = self._serial_lib.Serial(
                    dev_path, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1.0
                )
                return True
            except Exception as e:
                self._append_log(f"[Chiller] Serial open error: {e}")
                self._serial = None
                return False
        # No pyserial; simulate success so the UI is usable.
        return True

    def _disconnect_device(self):
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def _send_setpoint(self, temp_c: float) -> bool:
        """
        Replace with your device's actual protocol.
        Example SCPI-like: 'TEMP {value}\n'
        """
        if self._serial:
            try:
                cmd = f"TEMP {temp_c:.2f}\n".encode("ascii")
                self._serial.write(cmd)
                return True
            except Exception as e:
                self._append_log(f"[Chiller] Write error: {e}")
                return False
        # Simulate success without hardware
        return True

    def _poll_status(self):
        """
        Optional: read status/actual temperature periodically and append to log.
        Implement if your device supports it.
        """
        if self._serial:
            try:
                if self._serial.in_waiting:
                    data = self._serial.read(self._serial.in_waiting).decode(errors="ignore")
                    if data:
                        for line in data.splitlines():
                            self._append_log(f"[Chiller] {line}")
            except Exception as e:
                self._append_log(f"[Chiller] Read error: {e}")
