# chiller_panel.py
import sys, os, json, platform, glob
from pathlib import Path
from PyQt5.QtWidgets import (
    QHBoxLayout, QFormLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSlot, QProcess, QProcessEnvironment, QTimer
from PyQt5.QtGui import QFont
from panel import Panel
import qt_ansi

MAIN_DIR = Path(__file__).parent.parent
WORKER_PATH = MAIN_DIR / "src" / "julabo.py"

class ChillerPanel(Panel):
    """
    Chiller control panel using a separate worker process (/src/julabo.py)
    so device I/O is isolated from the GUI and other panels.
    """

    def __init__(self, title="Chiller"):
        super().__init__(title)

        # ---------- styles ----------
        self.setObjectName("chillerPanel")
        self.setStyleSheet("""
        #chillerPanel, #chillerPanel QWidget { color: #ffffff; }
        QLabel { color: #ffffff; }

        QComboBox, QTextEdit {
            color: #ffffff;
            border: 1px solid #374151;
            border-radius: 6px;
            padding: 4px 6px;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
            background-color: transparent;
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

        QPushButton#blueButton { 
            background-color: #2563eb; 
            color: #ffffff;}
        QPushButton#blueButton:hover  { background-color: #1d4ed8; }
        QPushButton#blueButton:pressed{ background-color: #1e40af; }

        QPushButton#redButton {
            background-color: #ef4444;
            color: #ffffff;
        }
        QPushButton#redButton:hover  { background-color: #dc2626; }
        QPushButton#redButton:pressed{ background-color: #b91c1c; }
        """)

        # ---------- spacer ----------
        top_pad = max(24, self.fontMetrics().height() + 8)
        self.subgrid.setRowMinimumHeight(0, top_pad)
        row0 = 1

        # ---------- form: device + connect ----------
        form = QFormLayout()

        # dev_row = QHBoxLayout()
        # self.dev_combo = QComboBox()
        # self.btn_refresh = QPushButton("Refresh")
        # self.btn_refresh.clicked.connect(self._refresh_ports)
        # dev_row.addWidget(self.dev_combo, 1)
        # dev_row.addWidget(self.btn_refresh)
        # form.addRow("Device:", self.dev_combo)
        dev_row = QHBoxLayout()
        self.dev_combo = QComboBox()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_ports)
        dev_row.addWidget(self.dev_combo, 1)
        dev_row.addWidget(self.btn_refresh)
        form.addRow("Device:", dev_row)   # <-- was self.dev_combo; now add the whole row   

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
        self.temp_spin.setRange(-20.0, 120.0)
        self.temp_spin.setValue(25.00)
        self.temp_spin.setSuffix(" °C")

        self.btn_set = QPushButton("Set Temp")
        self.btn_set.setEnabled(False)

        # Run button to power on / start circulation
        self.btn_run = QPushButton("Run")
        self.btn_run.setObjectName("blueButton")   # <-- make it blue
        self.btn_run.setEnabled(False)
        self._powered = False

        temp_row.addWidget(QLabel("Setpoint:"))
        temp_row.addWidget(self.temp_spin)
        temp_row.addWidget(self.btn_set)
        temp_row.addWidget(self.btn_run)      # add it to the row

        # ---------- info ----------
        info_row = QHBoxLayout()
        self.lbl_current_temp = QLabel("Current Temp: -- °C")
        self.lbl_current_temp.setFont(QFont("Arial", 16, QFont.Bold))
        self.lbl_status_onoff = QLabel("Status: --")
        self.lbl_status_onoff.setFont(QFont("Arial", 16, QFont.Bold))
        info_row.addWidget(self.lbl_current_temp)
        info_row.addWidget(self.lbl_status_onoff)

        # ---------- log (ANSI + Unicode) ----------
        self.log = QTextEdit()
        qt_ansi.configure_textedit(self.log, wrap=True)
        self._ansi_sink = qt_ansi.AnsiLogSink(self.log, cr_mode="newline")

        # ---------- layout ----------
        self.subgrid.addLayout(form,        row0 + 0, 0)
        self.subgrid.addLayout(connect_row, row0 + 1, 0)
        self.subgrid.addLayout(temp_row,    row0 + 2, 0)
        self.subgrid.addLayout(info_row,    row0 + 3, 0)
        self.subgrid.addWidget(self.log,    row0 + 4, 0)
        self.subgrid.setRowStretch(row0 + 4, 1)

        # ---------- worker process ----------
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("LANG", "en_US.UTF-8")
        env.insert("LC_ALL", "en_US.UTF-8")
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read_worker_output)
        self.proc.started.connect(self._worker_started)
        self.proc.finished.connect(self._worker_finished)
        self.proc.errorOccurred.connect(self._worker_error)

        # ---------- signals ----------
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.btn_set.clicked.connect(self._on_set_clicked)
        self.btn_run.clicked.connect(self._on_run_clicked)  

        # ---------- state ----------
        self._connected = False
        self._refresh_ports()

    # ===================== ports =====================

    def _refresh_ports(self):
        """Populate the device combo with available serial/USB devices (Linux/macOS)."""
        prev = self.dev_combo.currentData()
        entries, seen = [], set()

        try:
            from serial.tools import list_ports
            for p in list_ports.comports():
                dev = p.device
                if sys.platform == "darwin" and dev.startswith("/dev/tty."):
                    continue
                label = dev
                extra = " — ".join(
                    s for s in [p.manufacturer or "", p.product or p.description or ""]
                    if s
                )
                if extra:
                    label += f" — {extra}"
                if p.vid is not None and p.pid is not None:
                    label += f" (VID:PID={p.vid:04x}:{p.pid:04x})"
                if dev not in seen:
                    entries.append((dev, label)); seen.add(dev)
        except Exception:
            patterns = (
                ["/dev/cu.usbserial*", "/dev/cu.usbmodem*"] if sys.platform == "darwin"
                else ["/dev/serial/by-id/*", "/dev/ttyUSB*", "/dev/ttyACM*"]
            )
            for pat in patterns:
                for path in sorted(glob.glob(pat)):
                    if "/dev/serial/by-id/" in path:
                        dev = os.path.realpath(path)
                        label = f"{os.path.basename(path)} \u2192 {dev}"
                    else:
                        dev = path
                        if sys.platform == "darwin" and dev.startswith("/dev/tty."):
                            continue
                        label = dev
                    if dev not in seen:
                        entries.append((dev, label)); seen.add(dev)

        if not entries:
            entries = [("", "(no serial devices found)")]

        def sort_key(item):
            dev = item[0]; score = 0
            if "usbserial" in dev: score = -3
            elif "usbmodem" in dev: score = -2
            elif "ttyACM" in dev: score = -1
            return (score, dev)
        entries.sort(key=sort_key)

        self.dev_combo.blockSignals(True)
        self.dev_combo.clear()
        for dev, label in entries:
            self.dev_combo.addItem(label, userData=dev)

        idx = -1
        if prev:
            for i in range(self.dev_combo.count()):
                if self.dev_combo.itemData(i) == prev:
                    idx = i; break
        if idx < 0:
            for i in range(self.dev_combo.count()):
                if self.dev_combo.itemData(i):
                    idx = i; break
            if idx < 0: idx = 0
        self.dev_combo.setCurrentIndex(idx)
        self.dev_combo.blockSignals(False)

    # ===================== connect / disconnect =====================

    @pyqtSlot()
    def _on_connect_clicked(self):
        if self._connected or self.proc.state() != QProcess.NotRunning:
            self._append_log("[Chiller] Disconnecting…")
            self.btn_connect.setEnabled(False)
            self.proc.terminate()
            QTimer.singleShot(800, lambda: self.proc.kill() if self.proc.state() != QProcess.NotRunning else None)
            return

        dev = self.dev_combo.currentData()
        if not dev:
            self._append_log("[Chiller] Please select a valid serial device.")
            return

        cmd = sys.executable
        args = ["-u", str(WORKER_PATH), "--device", dev, "--sample_time", "1.0"]
        self._append_log(f"[Chiller] Launching worker: {cmd} {' '.join(args)}")
        self.btn_connect.setEnabled(False)
        self.btn_set.setEnabled(False)
        self.btn_run.setEnabled(False)
        self.proc.setWorkingDirectory(str(MAIN_DIR))
        self.proc.start(cmd, args)

    def _worker_started(self):
        self._append_log("[Chiller] Worker started.")
        self.btn_connect.setEnabled(True)
        self.btn_connect.setText("Disconnect")
        self.lbl_status.setText("Connecting…")

    def _worker_finished(self, code:int, status:QProcess.ExitStatus):
        self._ansi_sink.flush()
        self._append_log(f"[Chiller] Worker exited (code={code}, status={int(status)}).")
        self._set_connected_ui(False)

    def _worker_error(self, err: QProcess.ProcessError):
        self._append_log(f"[Chiller] Worker error: {err}.")
        self._set_connected_ui(False)

    # ===================== send commands =====================

    @pyqtSlot()
    def _on_set_clicked(self):
        if not self._connected:
            self._append_log("[Chiller] Not connected.")
            return
        sp = float(self.temp_spin.value())
        self._send_cmd({"cmd":"set_temp","value":sp})
        self._append_log(f"[Chiller] Setpoint request: {sp:.2f} °C")

    
    @pyqtSlot()
    def _on_run_clicked(self):
        """Toggle power: ON → OFF, OFF → ON."""
        if not self._connected:
            self._append_log("[Chiller] Not connected.")
            return

        # Disable until we get ack/status back to prevent double clicks
        self.btn_run.setEnabled(False)

        if self._powered:
            self._send_cmd({"cmd": "power", "on": False})
            self._append_log("[Chiller] Power OFF requested.")
        else:
            self._send_cmd({"cmd": "power", "on": True})
            self._append_log("[Chiller] Power ON requested.")

        # Optional: ask for a fresh status snapshot
        self._send_cmd({"cmd": "status"})

    def _send_cmd(self, obj):
        if self.proc.state() == QProcess.NotRunning:
            self._append_log("[Chiller] Worker not running.")
            return
        data = (json.dumps(obj) + "\n").encode("utf-8")
        self.proc.write(data)

    # ===================== process output =====================

    def _read_worker_output(self):
        data = bytes(self.proc.readAllStandardOutput())
        if not data:
            return
        text = data.decode("utf-8", errors="replace")
        for raw in text.splitlines():
            if not raw.strip():
                continue
            try:
                msg = json.loads(raw)
                self._handle_event(msg)
            except Exception:
                self._ansi_sink.feed(raw + "\n")

    def _handle_event(self, msg: dict):
        et = msg.get("event")

        if et == "connected":
            self._append_log(f"[Chiller] Connected to {msg.get('dev')}")
            self._set_connected_ui(True)
            self.lbl_status_onoff.setText("Status: --")
            # ask worker for an initial status snapshot
            self._send_cmd({"cmd": "status"})
            return

        if et == "disconnected":
            self._append_log("[Chiller] Disconnected.")
            self._set_connected_ui(False)
            return

        if et == "temp":
            try:
                val = float(msg.get("value"))
                self.lbl_current_temp.setText(f"Current Temp: {val:.2f} °C")
            except Exception:
                pass
            return

        if et == "status":
            sp  = msg.get("setpoint")
            pv  = msg.get("temperature")
            pwr = msg.get("power")

            if sp is not None:
                try: self.temp_spin.setValue(float(sp))
                except Exception: pass

            if pv is not None:
                try: self.lbl_current_temp.setText(f"Current Temp: {float(pv):.2f} °C")
                except Exception: pass

            if pwr is not None:
                on = self._to_bool(pwr)
                self._update_power_ui(on)  # <<< flips Run <-> Power Off (blue/red)
                self.lbl_status_onoff.setText("Status: ON" if on else "Status: OFF")

            if self._connected:
                self.btn_run.setEnabled(True)  # re-enable toggle once we have state
            return

        if et == "ack":
            # reflect power change immediately when the worker acks it
            if msg.get("cmd") == "power":
                on = self._to_bool(msg.get("on"))
                self._update_power_ui(on)
                self.lbl_status_onoff.setText("Status: ON" if on else "Status: OFF")
                if self._connected:
                    self.btn_run.setEnabled(True)
            self._append_log(f"[Chiller] ACK: {msg}")
            return

        if et == "warn":
            self._append_log(f"[Chiller] WARN: {msg}")
            return

        if et == "error":
            self._append_log(f"\x1b[31m[Chiller] ERROR: {msg.get('message')}\x1b[0m")
            return

        # Fallback: show anything unknown
        self._append_log(f"[Chiller] {msg}")



    # ===================== helpers =====================

    def _append_log(self, s: str):
        self._ansi_sink.feed(s.rstrip("\n") + "\n")

    def _set_connected_ui(self, ok: bool):
        self._connected = ok
        self.lbl_status.setText("Connected" if ok else "Disconnected")
        self.btn_connect.setText("Disconnect" if ok else "Connect")
        self.btn_connect.setEnabled(True)
        self.btn_set.setEnabled(ok)
        self.btn_run.setEnabled(ok)   # enable Run only when connected
        if not ok:
            self._update_power_ui(False)

    def _apply_button_style(self, btn: QPushButton, object_name: str):
        """Re-apply style after changing objectName."""
        btn.setObjectName(object_name)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()
    
    def _to_bool(self, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("on", "true", "1", "yes", "y", "enabled"):
                return True
            if s in ("off", "false", "0", "no", "n", "disabled"):
                return False
        # default safe: treat unknown as OFF
        return False

    def _update_power_ui(self, on: bool):
        self._powered = bool(on)
        if self._powered:
            self.btn_run.setText("Power Off")
            self._apply_button_style(self.btn_run, "redButton")
        else:
            self.btn_run.setText("Run")
            self._apply_button_style(self.btn_run, "blueButton")
