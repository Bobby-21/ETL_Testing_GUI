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
# src_dir = MAIN_DIR / "src"
# sys.path.append(str(src_dir))

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
        """)

        # ---------- spacer ----------
        top_pad = max(24, self.fontMetrics().height() + 8)
        self.subgrid.setRowMinimumHeight(0, top_pad)
        row0 = 1

        # ---------- form: device + connect ----------
        form = QFormLayout()

        dev_row = QHBoxLayout()
        self.dev_combo = QComboBox()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_ports)
        dev_row.addWidget(self.dev_combo, 1)
        dev_row.addWidget(self.btn_refresh)
        form.addRow("Device:", self.dev_combo)

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

        temp_row.addWidget(QLabel("Setpoint:"))
        temp_row.addWidget(self.temp_spin)
        temp_row.addWidget(self.btn_set)

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

        # ---------- state ----------
        self._connected = False
        self._refresh_ports()

    # ===================== ports =====================

    def _refresh_ports(self):
        """Populate the device combo with available serial/USB devices (Linux/macOS)."""
        prev = self.dev_combo.currentData()  # remember selection to restore if still present
        entries = []
        seen = set()

        try:
            # Preferred: pyserial, rich metadata
            from serial.tools import list_ports
            for p in list_ports.comports():
                dev = p.device
                # On mac, prefer the "cu.*" device for outgoing connections
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
                    entries.append((dev, label))
                    seen.add(dev)

        except Exception:
            # Fallback: glob common device names
            patterns = (
                ["/dev/cu.usbserial*", "/dev/cu.usbmodem*"]  # macOS
                if sys.platform == "darwin"
                else ["/dev/serial/by-id/*", "/dev/ttyUSB*", "/dev/ttyACM*"]  # Linux
            )
            for pat in patterns:
                for path in sorted(glob.glob(pat)):
                    # For Linux by-id, show the by-id name but connect to the resolved device
                    if "/dev/serial/by-id/" in path:
                        dev = os.path.realpath(path)
                        label = f"{os.path.basename(path)} \u2192 {dev}"
                    else:
                        dev = path
                        # On mac, skip /dev/tty.* in favor of /dev/cu.*
                        if sys.platform == "darwin" and dev.startswith("/dev/tty."):
                            continue
                        label = dev
                    if dev not in seen:
                        entries.append((dev, label))
                        seen.add(dev)

        # Nothing found
        if not entries:
            entries = [("", "(no serial devices found)")]

        # Prefer usbserial/usbmodem/ttyACM
        def sort_key(item):
            dev = item[0]
            score = 0
            if "usbserial" in dev: score = -3
            elif "usbmodem" in dev: score = -2
            elif "ttyACM" in dev: score = -1
            return (score, dev)
        entries.sort(key=sort_key)

        # Update combo and restore previous selection if possible
        self.dev_combo.blockSignals(True)
        self.dev_combo.clear()
        for dev, label in entries:
            self.dev_combo.addItem(label, userData=dev)

        idx = -1
        if prev:
            for i in range(self.dev_combo.count()):
                if self.dev_combo.itemData(i) == prev:
                    idx = i
                    break
        if idx < 0:
            # choose first real device
            for i in range(self.dev_combo.count()):
                if self.dev_combo.itemData(i):
                    idx = i
                    break
            if idx < 0:
                idx = 0
        self.dev_combo.setCurrentIndex(idx)
        self.dev_combo.blockSignals(False)
    

    # ===================== connect / disconnect =====================

    @pyqtSlot()
    def _on_connect_clicked(self):
        if self._connected or self.proc.state() != QProcess.NotRunning:
            self._append_log("[Chiller] Disconnecting…")
            self.btn_connect.setEnabled(False)
            # gentle stop then hard kill fallback
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
        self.proc.setWorkingDirectory(str(MAIN_DIR))  # so worker can import drivers/ via parents[1]
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
        # split to lines and parse JSON; non-JSON lines go to the ANSI sink
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
            self.lbl_status_onoff.setText("Status: ON")

        elif et == "disconnected":
            self._append_log("[Chiller] Disconnected.")
            self._set_connected_ui(False)

        elif et == "temp":
            try:
                val = float(msg.get("value"))
                self.lbl_current_temp.setText(f"Current Temp: {val:.2f} °C")
            except Exception:
                pass

        elif et == "status":
            sp = msg.get("setpoint")
            pv = msg.get("temperature")
            if sp is not None:
                try: self.temp_spin.setValue(float(sp))
                except Exception: pass
            if pv is not None:
                try: self.lbl_current_temp.setText(f"Current Temp: {float(pv):.2f} °C")
                except Exception: pass
            self.lbl_status_onoff.setText("Status: ON")

        elif et in ("ack","warn"):
            self._append_log(f"[Chiller] {et.upper()}: {msg}")

        elif et == "error":
            self._append_log(f"\x1b[31m[Chiller] ERROR: {msg.get('message')}\x1b[0m")

        else:
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
