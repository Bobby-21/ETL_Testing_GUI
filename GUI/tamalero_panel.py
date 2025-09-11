# tamalero_panel.py
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QPlainTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QProcess, QRegularExpression, pyqtSlot, QProcessEnvironment
from PyQt5.QtGui import QFont, QIntValidator, QRegularExpressionValidator

from panel import Panel

MAIN_DIR = Path(__file__).parent.parent
src_dir = MAIN_DIR / "src"
sys.path.append(str(src_dir))
# from tester import initiate_test  # (unused here)

class TamaleroPanel(Panel):
    def __init__(self, title="Tamalero"):
        super().__init__(title)

        # ---------- styles ----------
        self.setObjectName("tamaleroPanel")
        self.setStyleSheet("""
        #tamaleroPanel, #tamaleroPanel QWidget { color: #ffffff; }
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
        row0 = 1  # start placing content from this row

        # --------- Inputs (IP, Model ID) ----------
        form = QFormLayout()
        self.ip_edit = QLineEdit()
        # self.ip_edit.setPlaceholderText("e.g. 192.168.0.11")
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

        # --------- Dynamic parameter panel (appears below test selector) ----------
        self.params_widget = QWidget()
        self.params_form = QFormLayout(self.params_widget)
        self._build_params_for("module")  # default since that’s the only option now
        self.params_widget.setVisible(True)

        # --------- Local log view ----------
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.Monospace)
        self.log.setFont(mono)
        self.log.setPlaceholderText("Logs will appear here…")

        # --------- Layout ----------
        self.subgrid.setRowStretch(0, 0)
        self.subgrid.setRowStretch(1, 0)
        self.subgrid.setRowStretch(2, 0)
        self.subgrid.setRowStretch(3, 0)
        self.subgrid.setRowStretch(4, 1)
        self.subgrid.addLayout(form,            row0 + 0, 0)
        self.subgrid.addLayout(connect_row,     row0 + 1, 0)
        self.subgrid.addLayout(run_row,         row0 + 2, 0)
        self.subgrid.addWidget(self.params_widget, row0 + 3, 0)
        self.subgrid.addWidget(self.log,        row0 + 4, 0)

        # --------- Processes ----------
        # Shared unbuffered env for child Python processes
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")

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

        # --------- State ----------
        self._connected = False

    # ===================== UI helpers =====================

    def _append_log(self, text: str):
        self.log.appendPlainText(text.rstrip("\n"))
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

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
            # Configuration
            w_cfg = QLineEdit("modulev2")
            self.params_form.addRow("configuration:", w_cfg)
            self.param_widgets["configuration"] = w_cfg

            # Host
            w_host = QLineEdit("localhost")
            self.params_form.addRow("host:", w_host)
            self.param_widgets["host"] = w_host

            # module (ID within board)
            w_module = QLineEdit("1")
            w_module.setValidator(QIntValidator(0, 9999))
            self.params_form.addRow("module:", w_module)
            self.param_widgets["module"] = w_module

            # qinj (checkbox)
            w_qinj = QCheckBox("Enable charge injection (--qinj)")
            self.params_form.addRow("", w_qinj)
            self.param_widgets["qinj"] = w_qinj

            # charges (comma/space separated)
            w_charges = QLineEdit("")
            w_charges.setPlaceholderText("e.g. 10, 20, 30")
            self.params_form.addRow("charges:", w_charges)
            self.param_widgets["charges"] = w_charges
            w_charges.setEnabled(False)
            w_qinj.toggled.connect(w_charges.setEnabled)

            # nl1a (optional)
            w_nl1a = QLineEdit("")
            w_nl1a.setValidator(QIntValidator(1, 10**7))
            w_nl1a.setPlaceholderText("optional (e.g. 320)")
            self.params_form.addRow("nl1a:", w_nl1a)
            self.param_widgets["nl1a"] = w_nl1a

        else:
            # For future tests, add fields here.
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
            return

        ip = self.ip_edit.text().strip()
        model = self.model_edit.text().strip()

        if not ip or not self.ip_edit.hasAcceptableInput() or not self._is_valid_ipv4(ip):
            self._append_log("[Tamalero] Please enter a valid IPv4 address.")
            return
        if not model:
            self._append_log("[Tamalero] Please enter a valid Model ID.")
            return

        # Use the current Python interpreter and unbuffered mode
        cmd = sys.executable
        args = ["-u", str(MAIN_DIR / "module_test_sw" / "test_tamalero.py"),
                "--kcu", ip, "--verbose", "--power_up", "--adcs"]

        self._append_log(f"[Tamalero] Launching connection: {cmd} {' '.join(args)}")
        self.btn_connect.setEnabled(False)   # prevent double-click while starting
        self._set_controls_enabled(False)
        self.conn_proc.start(cmd, args)

    def _conn_started(self):
        # Don’t claim “Connected” yet; wait for success exit.
        self.btn_connect.setEnabled(True)
        self.btn_connect.setText("Cancel")
        self.lbl_status.setText("Connecting…")
        self._append_log("[Tamalero] Connection script started.")

    def _read_conn_output(self):
        data = bytes(self.conn_proc.readAllStandardOutput()).decode(errors="ignore")
        if data:
            for line in data.splitlines():
                self._append_log(line)

    def _conn_finished(self, code: int, status: QProcess.ExitStatus):
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

    def _conn_error(self, err: QProcess.ProcessError):
        self._append_log(f"[Tamalero] Connection process error: {err}.")
        self.btn_connect.setEnabled(True)
        self._connected = False
        self.btn_connect.setText("Connect")
        self.lbl_status.setText("Disconnected")
        self._set_controls_enabled(False)

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
            # Build args from the dynamic panel
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
                    # accept comma/space separated
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

    def _read_test_output(self):
        data = bytes(self.test_proc.readAllStandardOutput()).decode(errors="ignore")
        if data:
            for line in data.splitlines():
                self._append_log(line)

    def _proc_finished(self, code: int, status: QProcess.ExitStatus):
        ok = (status == QProcess.NormalExit and code == 0)
        if ok:
            self._append_log("[Tamalero] Test finished successfully.")
        else:
            self._append_log(f"[Tamalero] Test FAILED (code={code}, status={int(status)}).")

        self.btn_run.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.test_combo.setEnabled(True)
        self.params_widget.setEnabled(True)

    def _proc_error(self, err: QProcess.ProcessError):
        self._append_log(f"[Tamalero] Test process error: {err}.")
        self.btn_run.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.test_combo.setEnabled(True)
        self.params_widget.setEnabled(True)
