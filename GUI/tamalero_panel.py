# tamalero_panel.py
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QCheckBox, QSizePolicy,
    QShortcut, QFrame
)
from PyQt5.QtCore import Qt, QProcess, QRegularExpression, pyqtSlot, QProcessEnvironment, QTimer
from PyQt5.QtGui import QFont, QIntValidator, QRegularExpressionValidator, QKeySequence, QTextOption

from panel import Panel
import qt_ansi

MAIN_DIR = Path(__file__).parent.parent
src_dir = MAIN_DIR / "src"
sys.path.append(str(src_dir))

class TamaleroPanel(Panel):
    def __init__(self, title="Tamalero"):
        super().__init__(title)

        # ---------- styles ----------
        self.setObjectName("tamaleroPanel")
        self.setStyleSheet("""
        #tamaleroPanel, #tamaleroPanel QWidget { color: #ffffff; }
        QLabel { color: #ffffff; }

        QLineEdit, QPlainTextEdit, QTextEdit {
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

        QFrame#abortFrame {
            border: 3px solid #ef4444;
            border-radius: 12px;
            background-color: rgba(239,68,68,.08);
        }

        QPushButton#redButton {
            background-color: #ef4444;
            color: #ffffff;
            font-weight: 800;
            letter-spacing: 0.5px;
            border: 2px solid #7f1d1d;
            border-radius: 10px;
            padding: 10px 16px;
        }
        QPushButton#redButton:hover  { background-color: #dc2626; }
        QPushButton#redButton:pressed{ background-color: #b91c1c; }
        """)

        # ---------- spacer row to avoid overlapping the title ----------
        top_pad = max(24, self.fontMetrics().height() + 8)
        self.subgrid.setRowMinimumHeight(0, top_pad)
        row0 = 1  # start placing content from this row

        # --------- Inputs (IP, Model ID) ----------
        form = QFormLayout()
        self.ip_edit = QLineEdit()
        self.ip_edit.setText("192.168.0.15")
        ipv4_re = QRegularExpression(r"^\s*\d{1,3}(?:\.\d{1,3}){3}\s*$")
        self.ip_edit.setValidator(QRegularExpressionValidator(ipv4_re))

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Model ID (e.g. 204)")
        self.model_edit.setValidator(QIntValidator(0, 10**9))

        form.addRow("Chipset IP:", self.ip_edit)
        form.addRow("Model ID:", self.model_edit)

        # --------- Connect row ----------
        connect_row = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
        self.lbl_status = QLabel("Disconnected")
        connect_row.addWidget(self.btn_connect)
        connect_row.addWidget(self.lbl_status, 1, Qt.AlignLeft)

        # --------- Emergency stop (red box) ----------
        self.abort_frame = QFrame()
        self.abort_frame.setObjectName("abortFrame")
        ab_lay = QHBoxLayout(self.abort_frame)
        ab_lay.setContentsMargins(10, 10, 10, 10)

        self.btn_abort = QPushButton("EMERGENCY ABORT")
        self.btn_abort.setObjectName("redButton")
        self.btn_abort.setToolTip("Ctrl+Alt+X")
        self.btn_abort.setEnabled(False)
        self.btn_abort.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_abort.setMinimumHeight(56)
        ab_lay.addWidget(self.btn_abort)

        connect_row.addStretch(1)
        connect_row.addWidget(self.abort_frame)

        # --------- Test selection + Run row ----------
        run_row = QHBoxLayout()
        self.test_combo = QComboBox()
        self.test_combo.addItems(["module"])  # expand as needed
        self.btn_run = QPushButton("Run")
        self.btn_run.setEnabled(False)
        self.test_combo.setEnabled(False)
        run_row.addWidget(QLabel("Test:"))
        run_row.addWidget(self.test_combo, 1)
        run_row.addWidget(self.btn_run)

        # --------- Dynamic parameter panel ----------
        self.params_widget = QWidget()
        self.params_form = QFormLayout(self.params_widget)
        self._build_params_for("module")
        self.params_widget.setVisible(True)

        # --------- Log (ANSI + Unicode) ----------
        self.log = QTextEdit()
        qt_ansi.configure_textedit(self.log, wrap=True)
        self._ansi_sink = qt_ansi.AnsiLogSink(self.log)
        self.log.setWordWrapMode(QTextOption.WrapAnywhere)
        self.log.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.log.setMinimumHeight(300)

        # --------- Layout ----------
        self.subgrid.setRowStretch(row0 + 0, 0)
        self.subgrid.setRowStretch(row0 + 1, 0)
        self.subgrid.setRowStretch(row0 + 2, 0)
        self.subgrid.setRowStretch(row0 + 3, 0)
        self.subgrid.setRowStretch(row0 + 4, 1)

        self.subgrid.addLayout(form,                 row0 + 0, 0)
        self.subgrid.addLayout(connect_row,          row0 + 1, 0)
        self.subgrid.addLayout(run_row,              row0 + 2, 0)
        self.subgrid.addWidget(self.params_widget,   row0 + 3, 0)
        self.subgrid.addWidget(self.log,             row0 + 4, 0)

        # --------- Processes ----------
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("LANG", "en_US.UTF-8")
        env.insert("LC_ALL", "en_US.UTF-8")
        env.insert("TERM", "xterm-256color")
        env.insert("CLICOLOR_FORCE", "1")
        env.insert("FORCE_COLOR", "3")

        # connection process
        self.conn_proc = QProcess(self)
        self.conn_proc.setProcessEnvironment(env)
        self.conn_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.conn_proc.readyReadStandardOutput.connect(self._read_conn_output)
        self.conn_proc.finished.connect(self._conn_finished)
        self.conn_proc.errorOccurred.connect(self._conn_error)
        self.conn_proc.started.connect(self._conn_started)

        # module test process
        self.test_proc = QProcess(self)
        self.test_proc.setProcessEnvironment(env)
        self.test_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.test_proc.readyReadStandardOutput.connect(self._read_test_output)
        self.test_proc.finished.connect(self._proc_finished)
        self.test_proc.errorOccurred.connect(self._proc_error)

        # --------- Signals ----------
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.btn_run.clicked.connect(self._on_run_clicked)
        self.test_combo.currentTextChanged.connect(self._on_test_changed)

        # Emergency abort wiring + shortcut
        self.btn_abort.clicked.connect(self._on_abort_clicked)
        self.abort_shortcut = QShortcut(QKeySequence("Ctrl+Alt+X"), self)
        self.abort_shortcut.activated.connect(self._on_abort_clicked)
        self.abort_shortcut.setAutoRepeat(False)

        # --------- State ----------
        self._connected = False

    # ===================== UI helpers =====================

    def _append_log(self, text: str):
        # route status messages through the same sink so formatting is consistent
        self._ansi_sink.feed(text.rstrip("\n") + "\n")

    def _set_controls_enabled(self, enable_run: bool):
        self.btn_run.setEnabled(enable_run)
        self.test_combo.setEnabled(enable_run)
        self.params_widget.setEnabled(enable_run)

    # ===================== Validation =====================

    def _is_valid_ipv4(self, s: str) -> bool:
        parts = [p for p in s.strip().split(".") if p != ""]
        if len(parts) != 4:
            return False
        try:
            vals = [int(p) for p in parts]
        except ValueError:
            return False
        return all(0 <= v <= 255 for v in vals)

    # ===================== Param builders =====================

    def _clear_params_form(self):
        while self.params_form.count():
            item = self.params_form.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _build_params_for(self, test_name: str):
        self._clear_params_form()
        self.param_widgets = {}  # name -> widget

        if test_name == "module":
            w_cfg = QLineEdit("modulev2")
            self.params_form.addRow("configuration:", w_cfg)
            self.param_widgets["configuration"] = w_cfg

            w_host = QLineEdit("localhost")
            self.params_form.addRow("host:", w_host)
            self.param_widgets["host"] = w_host

            w_module = QLineEdit("1")
            w_module.setValidator(QIntValidator(0, 9999))
            self.params_form.addRow("module:", w_module)
            self.param_widgets["module"] = w_module

            w_qinj = QCheckBox("Enable charge injection (--qinj)")
            self.params_form.addRow("", w_qinj)
            self.param_widgets["qinj"] = w_qinj

            w_charges = QLineEdit("")
            w_charges.setPlaceholderText("e.g. 10, 20, 30")
            self.params_form.addRow("charges:", w_charges)
            self.param_widgets["charges"] = w_charges
            w_charges.setEnabled(False)
            w_qinj.toggled.connect(w_charges.setEnabled)

            w_nl1a = QLineEdit("")
            w_nl1a.setValidator(QIntValidator(1, 10**7))
            w_nl1a.setPlaceholderText("optional (e.g. 320)")
            self.params_form.addRow("nl1a:", w_nl1a)
            self.param_widgets["nl1a"] = w_nl1a

        else:
            info = QLabel("No parameters for this test.")
            self.params_form.addRow("", info)

    def _on_test_changed(self, name: str):
        self._build_params_for(name)
        self.params_widget.setVisible(True)

    # ===================== Connect / Disconnect =====================

    @pyqtSlot()
    def _on_connect_clicked(self):
        if self._connected:
            self._append_log("[Tamalero] Disconnecting…")
            try:
                if self.conn_proc.state() != QProcess.NotRunning:
                    self.conn_proc.kill()
            finally:
                self._connected = False
                self.btn_connect.setText("Connect")
                self.lbl_status.setText("Disconnected")
                self._set_controls_enabled(False)
                self._append_log("[Tamalero] Disconnected.")
                self._update_abort_enabled()
            return

        ip = self.ip_edit.text().strip()
        model = self.model_edit.text().strip()

        if not ip or not self.ip_edit.hasAcceptableInput() or not self._is_valid_ipv4(ip):
            self._append_log("[Tamalero] Please enter a valid IPv4 address.")
            return
        if not model:
            self._append_log("[Tamalero] Please enter a valid Model ID.")
            return

        cmd = sys.executable
        args = ["-u", str(MAIN_DIR / "module_test_sw" / "test_tamalero.py"),
                "--kcu", ip, "--verbose", "--power_up", "--adcs"]

        self._append_log(f"[Tamalero] Launching connection: {cmd} {' '.join(args)}")
        self.btn_connect.setEnabled(False)
        self._set_controls_enabled(False)
        self.conn_proc.start(cmd, args)
        self._update_abort_enabled()

    def _conn_started(self):
        self.btn_connect.setEnabled(True)
        self.btn_connect.setText("Cancel")
        self.lbl_status.setText("Connecting…")
        self._append_log("[Tamalero] Connection script started.")
        self._update_abort_enabled()

    def _read_conn_output(self):
        data = bytes(self.conn_proc.readAllStandardOutput())
        if data:
            self._ansi_sink.feed(data)

    def _conn_finished(self, code: int, status: QProcess.ExitStatus):
        self._ansi_sink.flush()
        ok = (status == QProcess.NormalExit and code == 0)
        if ok:
            self._append_log("[Tamalero] Connection script finished successfully.")
            self._connected = True
            self.lbl_status.setText("Ready")
            self.btn_connect.setText("Disconnect")
            self._set_controls_enabled(True)
        else:
            self._append_log(f"[Tamalero] Connection FAILED (code={code}, status={int(status)}).")
            self._connected = False
            self.lbl_status.setText("Disconnected")
            self.btn_connect.setText("Connect")
            self._set_controls_enabled(False)
        self._update_abort_enabled()

    def _conn_error(self, err: QProcess.ProcessError):
        self._append_log(f"[Tamalero] Connection process error: {err}.")
        self.btn_connect.setEnabled(True)
        self._connected = False
        self.btn_connect.setText("Connect")
        self.lbl_status.setText("Disconnected")
        self._set_controls_enabled(False)
        self._update_abort_enabled()

    # ===================== Run test (module) =====================

    @pyqtSlot()
    def _on_run_clicked(self):
        if not self._connected:
            self._append_log("[Tamalero] Not connected. Connect first.")
            return
        if self.test_proc.state() != QProcess.NotRunning:
            self._append_log("[Tamalero] A test is already running.")
            return

        ip = self.ip_edit.text().strip()
        model = self.model_edit.text().strip()
        test = self.test_combo.currentText()

        if test == "module":
            cfg   = self.param_widgets["configuration"].text().strip()
            host  = self.param_widgets["host"].text().strip() or "localhost"
            modno = self.param_widgets["module"].text().strip() or "1"
            qinj  = self.param_widgets["qinj"].isChecked()
            charges_raw = self.param_widgets["charges"].text().strip()
            nl1a  = self.param_widgets["nl1a"].text().strip()

            cmd = sys.executable
            args = ["-u", str(MAIN_DIR / "module_test_sw" / "test_module.py"),
                    "--configuration", cfg,
                    "--kcu", ip,
                    "--host", host,
                    "--moduleid", model,
                    "--test_chip",
                    "--module", modno]

            if qinj:
                args.append("--qinj")
                if charges_raw:
                    parts = [p for p in charges_raw.replace(",", " ").split() if p]
                    if parts:
                        args.append("--charges")
                        args.extend(parts)
            if nl1a:
                args.extend(["--nl1a", nl1a])

        else:
            self._append_log(f"[Tamalero] Unknown test: {test}")
            return

        self._append_log(f"[Tamalero] Launching test: {cmd} {' '.join(args)}")
        self.btn_run.setEnabled(False)
        self.btn_connect.setEnabled(False)
        self.test_combo.setEnabled(False)
        self.params_widget.setEnabled(False)
        self.test_proc.start(cmd, args)
        self._update_abort_enabled()

    def _read_test_output(self):
        data = bytes(self.test_proc.readAllStandardOutput())
        if data:
            self._ansi_sink.feed(data)

    def _proc_finished(self, code: int, status: QProcess.ExitStatus):
        self._ansi_sink.flush()
        ok = (status == QProcess.NormalExit and code == 0)
        if ok:
            self._append_log("[Tamalero] Test finished successfully.")
        else:
            self._append_log(f"[Tamalero] Test FAILED (code={code}, status={int(status)}).")

        self.btn_run.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.test_combo.setEnabled(True)
        self.params_widget.setEnabled(True)
        self._update_abort_enabled()

    def _proc_error(self, err: QProcess.ProcessError):
        self._append_log(f"[Tamalero] Test process error: {err}.")
        self.btn_run.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.test_combo.setEnabled(True)
        self.params_widget.setEnabled(True)
        self._update_abort_enabled()

    # ===================== Emergency abort =====================
    def _update_abort_enabled(self):
        running = (self.conn_proc.state() != QProcess.NotRunning) or \
                  (self.test_proc.state() != QProcess.NotRunning)
        self.btn_abort.setEnabled(running)

    def _abort_proc(self, proc: QProcess, name: str, grace_ms: int = 750):
        if proc.state() == QProcess.NotRunning:
            return False
        self._append_log(f"[Tamalero] EMERGENCY ABORT → {name} (pid={int(proc.processId())})")
        self.lbl_status.setText("Aborting…")
        proc.terminate()
        QTimer.singleShot(grace_ms, lambda: proc.kill() if proc.state() != QProcess.NotRunning else None)
        return True

    @pyqtSlot()
    def _on_abort_clicked(self):
        any_aborted = False
        if self.test_proc.state() != QProcess.NotRunning:
            any_aborted |= self._abort_proc(self.test_proc, "test")
        if self.conn_proc.state() != QProcess.NotRunning:
            any_aborted |= self._abort_proc(self.conn_proc, "connection")
        if not any_aborted:
            self._append_log("[Tamalero] No active Tamalero process to abort.")
        self._update_abort_enabled()
