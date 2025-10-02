# GUI/tamalero_panel.py
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QCheckBox, QSizePolicy,
    QShortcut, QFrame
)
from PyQt5.QtCore import Qt, pyqtSlot, QRegularExpression
from PyQt5.QtGui import QFont, QIntValidator, QRegularExpressionValidator, QKeySequence, QTextOption 

from panel import Panel
import qt_ansi

# repo root / src on path (keep your original behavior)
MAIN_DIR = Path(__file__).parent.parent
src_dir = MAIN_DIR / "src"
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

# new client
from src.devices.tamalero.client import TamaleroClient


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
        self.model_edit.setText("204")
        self.model_edit.setValidator(QIntValidator(0, 10**9))

        form.addRow("KCU IP:", self.ip_edit)
        form.addRow("Module ID:", self.model_edit)

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

        # --------- Dynamic parameter panel (2-column) ----------
        self.params_widget = QWidget()
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

        # --------- Client (single worker controlling both scripts) ----------
        self.client = TamaleroClient(self)
        self.client.log.connect(self._ansi_sink.feed)
        self.client.ready.connect(self._on_ready)
        self.client.error.connect(self._on_error)
        self.client.warn.connect(lambda w: self._append_log(f"[Tamalero] WARN: {w}"))
        self.client.disconnected.connect(self._on_disconnected)
        self.client.status.connect(self._on_status)
        self.client.conn_started.connect(self._on_conn_started)
        self.client.conn_finished.connect(self._on_conn_finished)
        self.client.test_started.connect(self._on_test_started)
        self.client.test_finished.connect(self._on_test_finished)

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
        self._connected = False              # becomes True when conn script finishes OK
        self._conn_running = False           # live connection script
        self._test_running = False           # live test script

    # ===================== UI helpers =====================

    def _append_log(self, text: str):
        self._ansi_sink.feed(text.rstrip("\n") + "\n")

    def _set_controls_enabled(self, enable_run: bool):
        self.btn_run.setEnabled(enable_run)
        self.test_combo.setEnabled(enable_run)
        self.params_widget.setEnabled(enable_run)

    def _update_abort_enabled(self):
        running = self._conn_running or self._test_running or self.client.isRunning()
        self.btn_abort.setEnabled(running)

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

    def _set_params_layout(self, layout):
        """Replace params_widget's layout safely (clean up children)."""
        old = self.params_widget.layout()
        if old is not None:
            def _clear(lay):
                while lay.count():
                    it = lay.takeAt(0)
                    w = it.widget()
                    if w: w.deleteLater()
                    sub = it.layout()
                    if sub:
                        _clear(sub)
                        sub.deleteLater()
            _clear(old)
            old.deleteLater()
        self.params_widget.setLayout(layout)

    def _clear_params_form(self):
        self._set_params_layout(QHBoxLayout())

    def _build_params_for(self, test_name: str):
        self.param_widgets = {}  # name -> widget

        left  = QFormLayout()
        right = QFormLayout()
        for f in (left, right):
            f.setLabelAlignment(Qt.AlignRight)
            f.setFormAlignment(Qt.AlignTop)
            f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            f.setHorizontalSpacing(12)
            f.setVerticalSpacing(8)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)
        row.addLayout(left, 1)
        row.addLayout(right, 1)

        if test_name == "module":
            # ---------- LEFT: basic ----------
            w_cfg = QLineEdit("modulev2")
            left.addRow("configuration:", w_cfg)
            self.param_widgets["configuration"] = w_cfg

            w_host = QLineEdit("localhost")
            left.addRow("host:", w_host)
            self.param_widgets["host"] = w_host

            w_module = QLineEdit("1")
            w_module.setValidator(QIntValidator(0, 9999))
            left.addRow("module:", w_module)
            self.param_widgets["module"] = w_module

            # ---------- RIGHT: qinj/charges/nl1a ----------
            w_qinj = QCheckBox("Enable charge injection (--qinj)")
            right.addRow("", w_qinj)
            self.param_widgets["qinj"] = w_qinj

            w_charges = QLineEdit("")
            w_charges.setPlaceholderText("e.g. 10, 20, 30")
            right.addRow("charges:", w_charges)
            self.param_widgets["charges"] = w_charges
            w_charges.setEnabled(False)
            w_qinj.toggled.connect(w_charges.setEnabled)

            w_nl1a = QLineEdit("")
            w_nl1a.setValidator(QIntValidator(1, 10**7))
            w_nl1a.setPlaceholderText("optional (e.g. 320)")
            right.addRow("nl1a:", w_nl1a)
            self.param_widgets["nl1a"] = w_nl1a
        else:
            left.addRow("", QLabel("No parameters for this test."))

        self._set_params_layout(row)

    def _on_test_changed(self, name: str):
        self._build_params_for(name)
        self.params_widget.setVisible(True)

    # ===================== Connect / Disconnect =====================

    @pyqtSlot()
    def _on_connect_clicked(self):
        # Toggle: if we consider ourselves connected or the worker is running, act as disconnect
        if self.client.isRunning() and (self._connected or self._conn_running or self._test_running):
            self._append_log("[Tamalero] Disconnecting…")
            self.lbl_status.setText("Disconnecting…")
            self._set_controls_enabled(False)
            self.client.stop()
            # states will be reset in _on_disconnected()
            return

        # Start worker & launch connection script
        ip = self.ip_edit.text().strip()
        model = self.model_edit.text().strip()
        if not ip or not self.ip_edit.hasAcceptableInput() or not self._is_valid_ipv4(ip):
            self._append_log("[Tamalero] Please enter a valid IPv4 address.")
            return
        if not model:
            self._append_log("[Tamalero] Please enter a valid Model ID.")
            return

        if not self.client.isRunning():
            self._append_log("[Tamalero] Starting worker…")
            self.client.start()

        self._append_log("[Tamalero] Launching connection…")
        self.btn_connect.setEnabled(False)
        self._set_controls_enabled(False)
        self.client.connect_kcu(kcu=ip, verbose=True, power_up=True, adcs=True)
        self._update_abort_enabled()

    # ===================== Run test (module) =====================

    @pyqtSlot()
    def _on_run_clicked(self):
        if not self._connected:
            self._append_log("[Tamalero] Not connected. Connect first.")
            return
        if self._test_running:
            self._append_log("[Tamalero] A test is already running.")
            return

        ip = self.ip_edit.text().strip()
        model = self.model_edit.text().strip()
        test = self.test_combo.currentText()

        if test != "module":
            self._append_log(f"[Tamalero] Unknown test: {test}")
            return

        cfg   = self.param_widgets["configuration"].text().strip()
        host  = self.param_widgets["host"].text().strip() or "localhost"
        modno = self.param_widgets["module"].text().strip() or "1"
        qinj  = self.param_widgets["qinj"].isChecked()
        charges_raw = self.param_widgets["charges"].text().strip()
        nl1a  = self.param_widgets["nl1a"].text().strip() or None

        charges_list = []
        if qinj and charges_raw:
            charges_list = [p for p in charges_raw.replace(",", " ").split() if p]

        self._append_log("[Tamalero] Launching test…")
        self.btn_run.setEnabled(False)
        self.btn_connect.setEnabled(False)
        self.test_combo.setEnabled(False)
        self.params_widget.setEnabled(False)

        if not self.client.isRunning():
            self.client.start()

        self.client.run_module(
            configuration=cfg,
            kcu=ip,
            host=host,
            moduleid=model,
            module=modno,
            qinj=qinj,
            charges=charges_list,
            nl1a=nl1a,
        )
        self._update_abort_enabled()

    # ===================== Emergency abort =====================

    @pyqtSlot()
    def _on_abort_clicked(self):
        self._append_log("[Tamalero] EMERGENCY ABORT requested.")
        self.lbl_status.setText("Aborting…")
        self.client.abort()
        self._update_abort_enabled()

    # ===================== Client signal handlers =====================

    def _on_ready(self):
        # Worker is alive and ready to take commands
        self._append_log("[Tamalero] Worker ready.")
        self.lbl_status.setText("Ready")
        self.btn_connect.setEnabled(True)
        self._update_abort_enabled()

    def _on_status(self, st: dict):
        self._conn_running = bool(st.get("conn_running", False))
        self._test_running = bool(st.get("test_running", False))
        self._update_abort_enabled()

    def _on_conn_started(self, args: dict):
        self._conn_running = True
        self._connected = False
        self.lbl_status.setText("Connecting…")
        self._append_log(f"[Tamalero] Connection started: {args}")
        self._update_abort_enabled()

    def _on_conn_finished(self, code: int):
        self._conn_running = False
        ok = (code == 0)
        if ok:
            self._connected = True
            self.lbl_status.setText("Ready")
            self._append_log("[Tamalero] Connection finished successfully.")
            self.btn_connect.setText("Disconnect")
            self._set_controls_enabled(True)
        else:
            self._connected = False
            self.lbl_status.setText("Disconnected")
            self._append_log(f"[Tamalero] Connection FAILED (code={code}).")
            self.btn_connect.setText("Connect")
            self._set_controls_enabled(False)
        self.btn_connect.setEnabled(True)
        self._update_abort_enabled()

    def _on_test_started(self, args: dict):
        self._test_running = True
        self._append_log(f"[Tamalero] Test started: {args}")
        self.lbl_status.setText("Running test…")
        self._update_abort_enabled()

    def _on_test_finished(self, code: int):
        self._test_running = False
        ok = (code == 0)
        if ok:
            self._append_log("[Tamalero] Test finished successfully.")
        else:
            self._append_log(f"[Tamalero] Test FAILED (code={code}).")
        # restore controls
        self.btn_run.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.test_combo.setEnabled(True)
        self.params_widget.setEnabled(True)
        self.lbl_status.setText("Ready" if self._connected else "Disconnected")
        self._update_abort_enabled()

    def _on_disconnected(self):
        # worker stopped (either user stop or crash)
        self._append_log("[Tamalero] Worker stopped.")
        self._connected = False
        self._conn_running = False
        self._test_running = False
        self.lbl_status.setText("Disconnected")
        self.btn_connect.setText("Connect")
        self.btn_connect.setEnabled(True)
        self._set_controls_enabled(False)
        self._update_abort_enabled()

    def _on_error(self, e: str):
        self._append_log(f"[Tamalero] ERROR: {e}")
        # keep UX consistent with your previous panel
        self.btn_connect.setEnabled(True)
        if not (self._conn_running or self._test_running):
            self._connected = False
            self.lbl_status.setText("Disconnected")
            self.btn_connect.setText("Connect")
            self._set_controls_enabled(False)
        self._update_abort_enabled()
