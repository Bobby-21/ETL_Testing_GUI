# results_panel.py
import sys, re
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QHBoxLayout, QFormLayout, QPushButton, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QSizePolicy, QTextEdit
)
from PyQt5.QtCore import Qt, QUrl, QProcess, QProcessEnvironment, pyqtSlot
from PyQt5.QtGui import QDesktopServices, QFont

from panel import Panel
import qt_ansi  # for colored, unicode-safe debug log

MAIN_DIR = Path(__file__).parent.parent
RESULTS_DIR = MAIN_DIR / "results"
PLOT_SCRIPT_PATH = MAIN_DIR / "module_test_sw" / "plot_board_summary.py"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)

class ResultsPanel(Panel):
    def __init__(self, title="Results"):
        super().__init__(title)

        self.setObjectName("resultsPanel")
        self.setStyleSheet("""
        #resultsPanel, #resultsPanel QWidget { color: #ffffff; }
        QLabel { color: #ffffff; }
        QLineEdit, QListWidget, QTextEdit {
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
        QPushButton#greenButton { background-color: #22c55e; color: #ffffff; }
        QPushButton#greenButton:hover { background-color: #16a34a; }
        QPushButton#greenButton:pressed { background-color: #15803d; }
        QPushButton#blueButton { background-color: #2563eb; color: #ffffff; }
        QPushButton#blueButton:hover { background-color: #1d4ed8; }
        QPushButton#blueButton:pressed { background-color: #1e40af; }
        """)

        # spacer for title
        top_pad = max(24, self.fontMetrics().height() + 8)
        self.subgrid.setRowMinimumHeight(0, top_pad)
        row0 = 1

        # ---- Module + controls
        form = QFormLayout()
        self.module_edit = QLineEdit()
        self.module_edit.setPlaceholderText("Enter Module ID (e.g. 204)")
        form.addRow("Module ID:", self.module_edit)

        ctrl_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_open = QPushButton("Open Folder")
        self.btn_open.setObjectName("greenButton")
        self.btn_open.setEnabled(False)
        self.btn_plot = QPushButton("Make Summary")
        self.btn_plot.setObjectName("blueButton")
        self.btn_plot.setEnabled(False)

        # NEW: debug toggle (expands/collapses a real log view)
        self.btn_debug = QPushButton("Debug ▼")
        self.btn_debug.setCheckable(True)
        self.btn_debug.setToolTip("Show/Hide full plot output (persistent)")

        ctrl_row.addWidget(self.btn_refresh)
        ctrl_row.addStretch(1)
        ctrl_row.addWidget(self.btn_debug)
        ctrl_row.addWidget(self.btn_open)
        ctrl_row.addWidget(self.btn_plot)

        # ---- List of result subdirectories
        self.list = QListWidget()
        self.list.setSelectionMode(self.list.SingleSelection)
        self.list.itemSelectionChanged.connect(self._update_buttons)
        self.list.itemDoubleClicked.connect(lambda _: self._open_selected())

        # ---- Single-line live status
        self.status_line = QLineEdit()
        self.status_line.setReadOnly(True)
        self.status_line.setPlaceholderText("Ready")
        mono = QFont("Courier New"); mono.setStyleHint(QFont.Monospace)
        self.status_line.setFont(mono)
        self.status_line.setClearButtonEnabled(True)
        self.status_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.status_line.setToolTip("Latest line from plot_board_summary.py")

        # ---- Hidden persistent debug log (colored + unicode)
        self.debug_log = QTextEdit()
        qt_ansi.configure_textedit(self.debug_log, wrap=True)
        self._ansi_debug = qt_ansi.AnsiLogSink(self.debug_log, cr_mode="newline")
        self.debug_log.setVisible(False)                     # hidden by default
        self.debug_log.setMinimumHeight(220)                 # bigger *only* when shown
        self.debug_log.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # layout
        self.subgrid.addLayout(form,              row0 + 0, 0)
        self.subgrid.addLayout(ctrl_row,          row0 + 1, 0)
        self.subgrid.addWidget(self.list,         row0 + 2, 0)
        self.subgrid.addWidget(self.status_line,  row0 + 3, 0)
        self.subgrid.addWidget(self.debug_log,    row0 + 4, 0)
        self.subgrid.setRowStretch(row0 + 2, 1)  # list grows
        self.subgrid.setRowStretch(row0 + 3, 0)  # status stays compact
        self.subgrid.setRowStretch(row0 + 4, 0)  # debug expands only when visible

        # ---- Plot process
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("LANG", "en_US.UTF-8")
        env.insert("LC_ALL", "en_US.UTF-8")

        self.plot_proc = QProcess(self)
        self.plot_proc.setProcessEnvironment(env)
        self.plot_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.plot_proc.readyReadStandardOutput.connect(self._read_plot_output)
        self.plot_proc.finished.connect(self._plot_finished)
        self.plot_proc.errorOccurred.connect(self._plot_error)
        self.plot_proc.started.connect(self._plot_started)

        # Signals
        self.btn_refresh.clicked.connect(self._refresh_list)
        self.btn_open.clicked.connect(self._open_selected)
        self.btn_plot.clicked.connect(self._run_summary)
        self.btn_debug.toggled.connect(self._toggle_debug)
        self.module_edit.returnPressed.connect(self._refresh_list)

        # state
        self._debug_on = False
        self._refresh_list()

    # ---------- Helpers ----------
    def _selected_path(self) -> Path:
        items = self.list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.UserRole)

    def _update_buttons(self):
        have_sel = self._selected_path() is not None
        idle = (self.plot_proc.state() == QProcess.NotRunning)
        self.btn_open.setEnabled(have_sel)
        self.btn_plot.setEnabled(have_sel and idle)

    def _set_status(self, text: str):
        self.status_line.setText(text)
        self.status_line.setCursorPosition(len(text))  # keep caret at end

    # ---------- Debug toggle ----------
    def _toggle_debug(self, checked: bool):
        self._debug_on = checked
        self.debug_log.setVisible(checked)
        self.btn_debug.setText("Debug ▲" if checked else "Debug ▼")
        # give it a little more space when open
        self.subgrid.setRowStretch(self.subgrid.indexOf(self.debug_log), 1 if checked else 0)

    # ---------- Refresh list ----------
    @pyqtSlot()
    def _refresh_list(self):
        self.list.clear()
        module_id = self.module_edit.text().strip()
        if not module_id:
            self._set_status("Enter a Module ID to search results/<module id>/")
            self._update_buttons()
            return

        base = RESULTS_DIR / module_id
        if not base.exists():
            self._set_status(f"No directory: {base}")
            self._update_buttons()
            return

        entries = []
        for p in base.iterdir():
            try:
                if p.is_dir():
                    mtime = p.stat().st_mtime
                    entries.append((p, mtime))
            except Exception:
                pass
        entries.sort(key=lambda t: t[1], reverse=True)

        if not entries:
            self._set_status(f"{base} has no subdirectories.")
        else:
            for path, mt in entries:
                ts = datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M:%S")
                item = QListWidgetItem(f"{path.name} — {ts}")
                item.setData(Qt.UserRole, path)
                self.list.addItem(item)
            self.list.setCurrentRow(0)

        self._update_buttons()

    # ---------- Open folder ----------
    @pyqtSlot()
    def _open_selected(self):
        path = self._selected_path()
        if not path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        self._set_status(f"Opened: {path}")

    # ---------- Run summary ----------
    @pyqtSlot()
    def _run_summary(self):
        if self.plot_proc.state() != QProcess.NotRunning:
            self._set_status("Plot already running.")
            return

        module_id = self.module_edit.text().strip()
        if not module_id:
            self._set_status("Module ID required.")
            return

        sel = self._selected_path()
        if not sel:
            self._set_status("Select a results folder first.")
            return

        if not PLOT_SCRIPT_PATH.exists():
            self._set_status(f"plot script not found: {PLOT_SCRIPT_PATH}")
            return

        # IMPORTANT: do not clear the debug log — we keep history across runs.
        # Append a timestamped separator instead.
        self._ansi_debug.feed(f"\n\x1b[90m---- Run @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ----\x1b[0m\n")

        cmd = sys.executable
        args = ["-u", str(PLOT_SCRIPT_PATH), "--input", str(sel), "--module", module_id]

        self._set_status(f"Launching: {cmd} {' '.join(args)}")
        self.btn_plot.setEnabled(False)
        self.plot_proc.setWorkingDirectory(str(MAIN_DIR))  # optional
        self.plot_proc.start(cmd, args)
        self._update_buttons()

    def _plot_started(self):
        self._set_status("Summary plot started…")

    def _read_plot_output(self):
        data = bytes(self.plot_proc.readAllStandardOutput())
        if not data:
            return
        # Always append to the persistent debug log (colors preserved).
        self._ansi_debug.feed(data)
        # And update the compact one-liner with the latest non-empty line (ANSI stripped)
        text = data.decode("utf-8", errors="replace")
        lines = [ln for ln in _strip_ansi(text).splitlines() if ln.strip()]
        if lines:
            self._set_status(lines[-1])

    def _plot_finished(self, code: int, status: QProcess.ExitStatus):
        # No clearing/flush that would remove history — just append a footer.
        ok = (status == QProcess.NormalExit and code == 0)
        msg = "Summary plot finished successfully." if ok else f"Plot FAILED (code={code}, status={int(status)})"
        self._ansi_debug.feed(("\x1b[92m" if ok else "\x1b[31m") + msg + "\x1b[0m\n")
        self._set_status(msg)
        self._update_buttons()

    def _plot_error(self, err: QProcess.ProcessError):
        msg = f"Plot process error: {err}"
        self._ansi_debug.feed(f"\x1b[31m{msg}\x1b[0m\n")
        self._set_status(msg)
        self._update_buttons()
