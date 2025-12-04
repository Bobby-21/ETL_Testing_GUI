# hv_panel.py
import csv
import time
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QPushButton, QLabel, QDoubleSpinBox, QSpinBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QFileDialog
)


class DummyHV(QObject):
    """
    Baseplate stub to represent an HV supply.
    Replace with your real driver (e.g., pyvisa, socket, serial, etc.).
    """
    def __init__(self):
        super().__init__()
        self._connected = False
        self._on = False
        self._vset = 0.0
        self._ilim = 0.1  # mA
        self._vread = 0.0
        self._iread = 0.0

    def connect(self, resource: str) -> bool:
        # TODO: implement real connect
        self._connected = True
        return True

    def disconnect(self):
        # TODO: implement real disconnect
        self._connected = False
        self._on = False

    def is_connected(self) -> bool:
        return self._connected

    def set_voltage(self, volts: float):
        self._vset = max(0.0, volts)

    def set_current_limit(self, milliamps: float):
        self._ilim = max(0.0, milliamps)

    def output_on(self, on: bool):
        if self._connected:
            self._on = on

    def read_voltage(self) -> float:
        # Simulate ramping toward setpoint when ON
        if self._on:
            self._vread += (self._vset - self._vread) * 0.25
        else:
            # decay to 0 when OFF
            self._vread *= 0.85
        return self._vread

    def read_current(self) -> float:
        # Simulate a weakly increasing current with voltage + tiny noise
        self._iread = min(self._ilim, 0.001 * self._vread + 0.0005 * (time.time() % 1))
        return self._iread


class HVPanel(QWidget):
    """
    Baseplate HV control + I–V logging panel.
    """
    logAdded = pyqtSignal(str, float, float)  # timestamp, V, I

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("HVPanel")
        self.setStyleSheet("""
            #HVPanel {
                background-color: #2c2c2c;
                color: #e8e8e8;
            }
            QGroupBox {
                border: 1px solid #5a5a5a;
                border-radius: 6px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
            }
            QLabel { color: #e8e8e8; }
        """)

        # --- Model / timers ---
        self.hv = DummyHV()
        self.poll_ms = 200
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_readback)
        self.poll_timer.start(self.poll_ms)

        # IV sweep timer
        self.sweep_timer = QTimer(self)
        self.sweep_timer.timeout.connect(self._iv_step)

        self.sweep_active = False
        self.sweep_start = 0.0
        self.sweep_stop = 0.0
        self.sweep_step = 0.0
        self.sweep_dwell_ms = 500
        self.sweep_next_setpoint = 0.0

        # --- UI sections ---
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_connection_box())
        root.addWidget(self._build_control_box())
        root.addWidget(self._build_readback_box())
        root.addWidget(self._build_sweep_box())
        root.addWidget(self._build_log_box())
        root.addStretch(1)

        # Connect log signal to table
        self.logAdded.connect(self._append_log_row)

    # ---------------------- UI builders ----------------------

    def _build_connection_box(self):
        box = QGroupBox("Connection")
        lay = QHBoxLayout(box)

        self.res_edit = QLineEdit("TCPIP::192.168.1.50::INSTR")
        self.btn_connect = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")

        self.btn_connect.clicked.connect(self._do_connect)
        self.btn_disconnect.clicked.connect(self._do_disconnect)

        lay.addWidget(QLabel("Resource:"))
        lay.addWidget(self.res_edit, 1)
        lay.addWidget(self.btn_connect)
        lay.addWidget(self.btn_disconnect)
        return box

    def _build_control_box(self):
        box = QGroupBox("Setpoints / Output")
        form = QFormLayout(box)

        self.volt_set = QDoubleSpinBox()
        self.volt_set.setRange(0.0, 5000.0)
        self.volt_set.setDecimals(1)
        self.volt_set.setSingleStep(10.0)
        self.volt_set.setSuffix(" V")

        self.curr_lim = QDoubleSpinBox()
        self.curr_lim.setRange(0.0, 20.0)  # mA
        self.curr_lim.setDecimals(3)
        self.curr_lim.setSingleStep(0.1)
        self.curr_lim.setSuffix(" mA")

        h = QHBoxLayout()
        self.btn_set = QPushButton("Apply Setpoints")
        self.chk_output = QCheckBox("Output ON")
        self.btn_set.clicked.connect(self._apply_setpoints)
        self.chk_output.stateChanged.connect(self._toggle_output)
        h.addWidget(self.btn_set)
        h.addWidget(self.chk_output)
        h.addStretch(1)

        form.addRow("Voltage Setpoint:", self.volt_set)
        form.addRow("Current Limit:", self.curr_lim)
        form.addRow(h)
        return box

    def _build_readback_box(self):
        box = QGroupBox("Readback")
        lay = QHBoxLayout(box)

        self.lbl_status = QLabel("Status: DISCONNECTED")
        self.lbl_v = QLabel("V = --.- V")
        self.lbl_i = QLabel("I = ---.--- mA")

        for w in (self.lbl_status, self.lbl_v, self.lbl_i):
            w.setMinimumWidth(140)

        lay.addWidget(self.lbl_status)
        lay.addSpacing(16)
        lay.addWidget(self.lbl_v)
        lay.addSpacing(16)
        lay.addWidget(self.lbl_i)
        lay.addStretch(1)
        return box

    def _build_sweep_box(self):
        box = QGroupBox("I–V Sweep")
        form = QFormLayout(box)

        self.sweep_vstart = QDoubleSpinBox()
        self.sweep_vstart.setRange(0.0, 5000.0)
        self.sweep_vstart.setDecimals(1)
        self.sweep_vstart.setSingleStep(10.0)
        self.sweep_vstart.setSuffix(" V")

        self.sweep_vstop = QDoubleSpinBox()
        self.sweep_vstop.setRange(0.0, 5000.0)
        self.sweep_vstop.setDecimals(1)
        self.sweep_vstop.setSingleStep(10.0)
        self.sweep_vstop.setSuffix(" V")

        self.sweep_vstep = QDoubleSpinBox()
        self.sweep_vstep.setRange(0.1, 1000.0)
        self.sweep_vstep.setDecimals(1)
        self.sweep_vstep.setSingleStep(1.0)
        self.sweep_vstep.setSuffix(" V")

        self.sweep_dwell = QSpinBox()
        self.sweep_dwell.setRange(100, 10000)
        self.sweep_dwell.setSingleStep(100)
        self.sweep_dwell.setSuffix(" ms")

        btns = QHBoxLayout()
        self.btn_sweep_start = QPushButton("Start Sweep")
        self.btn_sweep_stop = QPushButton("Stop")
        self.btn_sweep_start.clicked.connect(self._start_iv_sweep)
        self.btn_sweep_stop.clicked.connect(self._stop_iv_sweep)
        btns.addWidget(self.btn_sweep_start)
        btns.addWidget(self.btn_sweep_stop)
        btns.addStretch(1)

        form.addRow("Start Voltage:", self.sweep_vstart)
        form.addRow("Stop Voltage:", self.sweep_vstop)
        form.addRow("Step:", self.sweep_vstep)
        form.addRow("Dwell:", self.sweep_dwell)
        form.addRow(btns)
        return box

    def _build_log_box(self):
        box = QGroupBox("Log (Timestamp, V, I)")
        v = QVBoxLayout(box)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Voltage (V)", "Current (mA)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)

        btns = QHBoxLayout()
        self.btn_save = QPushButton("Save CSV")
        self.btn_clear = QPushButton("Clear Log")
        self.btn_save.clicked.connect(self._save_csv)
        self.btn_clear.clicked.connect(self._clear_log)
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_clear)
        btns.addStretch(1)

        v.addWidget(self.table)
        v.addLayout(btns)
        return box

    # ---------------------- Actions ----------------------

    def _do_connect(self):
        ok = self.hv.connect(self.res_edit.text().strip())
        self.lbl_status.setText("Status: CONNECTED" if ok else "Status: DISCONNECTED")

    def _do_disconnect(self):
        self.hv.disconnect()
        self.lbl_status.setText("Status: DISCONNECTED")

    def _apply_setpoints(self):
        self.hv.set_voltage(self.volt_set.value())
        self.hv.set_current_limit(self.curr_lim.value())

    def _toggle_output(self, state):
        self.hv.output_on(state == Qt.Checked)

    def _poll_readback(self):
        v = self.hv.read_voltage()
        i = self.hv.read_current()
        self.lbl_v.setText(f"V = {v:6.1f} V")
        self.lbl_i.setText(f"I = {i:7.3f} mA")
        # Optionally auto-log while sweeping
        if self.sweep_active:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logAdded.emit(ts, v, i)

    # ---------------------- I–V Sweep ----------------------

    def _start_iv_sweep(self):
        if not self.hv.is_connected():
            self.lbl_status.setText("Status: NOT CONNECTED")
            return

        self.sweep_start = self.sweep_vstart.value()
        self.sweep_stop = self.sweep_vstop.value()
        self.sweep_step = self.sweep_vstep.value()
        self.sweep_dwell_ms = self.sweep_dwell.value()

        if self.sweep_step <= 0.0:
            return

        # Initialize
        self.sweep_active = True
        self.sweep_next_setpoint = self.sweep_start
        self.hv.set_voltage(self.sweep_next_setpoint)
        self.hv.output_on(True)
        self.chk_output.setChecked(True)

        self.sweep_timer.start(self.sweep_dwell_ms)

    def _iv_step(self):
        if not self.sweep_active:
            self.sweep_timer.stop()
            return

        # Advance setpoint
        next_v = self.sweep_next_setpoint + self.sweep_step
        if (self.sweep_step > 0 and next_v > self.sweep_stop) or (self.sweep_step < 0 and next_v < self.sweep_stop):
            # finished
            self._stop_iv_sweep()
            return

        self.sweep_next_setpoint = next_v
        self.hv.set_voltage(self.sweep_next_setpoint)

    def _stop_iv_sweep(self):
        self.sweep_active = False
        self.sweep_timer.stop()

    # ---------------------- Log helpers ----------------------

    def _append_log_row(self, ts: str, v: float, i: float):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(ts))
        self.table.setItem(r, 1, QTableWidgetItem(f"{v:.3f}"))
        self.table.setItem(r, 2, QTableWidgetItem(f"{i:.6f}"))

    def _save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save I-V CSV", "iv_log.csv", "CSV Files (*.csv)")
        if not path:
            return
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            headers = [self.table.horizontalHeaderItem(c).text() for c in range(cols)]
            writer.writerow(headers)
            for r in range(rows):
                row = []
                for c in range(cols):
                    item = self.table.item(r, c)
                    row.append(item.text() if item else "")
                writer.writerow(row)

    def _clear_log(self):
        self.table.setRowCount(0)
