# src/devices/chiller/client.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from ...process_client import ProcessClient


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


class ChillerClient(QObject):
    """
    Process-managed client for the Julabo chiller.

    JSON events expected from worker (same as your julabo.py):
      - {"event":"connected","dev":<str>}
      - {"event":"disconnected"}
      - {"event":"temp","value":<float>}
      - {"event":"status","setpoint":<float>,"temperature":<float>,"power":<bool>}
      - {"event":"ack", ...}
      - {"event":"warn","message":<str>}
      - {"event":"error","message":<str>}
    """

    # lifecycle/logging
    started = pyqtSignal()
    finished = pyqtSignal(int)
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    warn = pyqtSignal(str)

    # device signals
    connected = pyqtSignal(str)         # dev path string
    disconnected = pyqtSignal()

    temp = pyqtSignal(float)            # periodic temperature metric
    status = pyqtSignal(dict)           # full status snapshot dict
    ack = pyqtSignal(dict)              # acks for set_temp/power/etc.

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._p = ProcessClient(self)
        self._p.textOutput.connect(self.log.emit)
        self._p.message.connect(self._route)
        self._p.errorOccurred.connect(self._on_proc_error)
        self._p.started.connect(self.started.emit)
        self._p.finished.connect(self._on_finished)

        root = _repo_root_from_here()
        self._cwd = root
        self._worker_path = root / "src" / "devices" / "chiller" / "worker.py"

        self._ever_connected = False
        self._connect_timer = QTimer(self)
        self._connect_timer.setSingleShot(True)
        self._connect_timer.timeout.connect(self._on_connect_timeout)

        self._connect_timeout_ms = 5000  # default 5s; can be overridden in start()

    # ---------------- lifecycle ----------------

    def start(self, *, device: str, sample_time: float = 1.0,
              extra_args: Optional[list] = None,
              connect_timeout: float = 5.0) -> None:
        """
        Launch the worker.

        Parameters
        ----------
        device : str
            Serial device path or resource string (e.g. /dev/ttyUSB0).
        sample_time : float
            Seconds between status/temperature polls in the worker.
        extra_args : list[str] (optional)
            Passed through to the underlying julabo.py if it supports more CLI.
        connect_timeout : float
            Max seconds to wait for a 'connected' event before aborting.
        """
        args = [
            "-u", str(self._worker_path),
            "--device", str(device),
            "--sample_time", str(float(sample_time)),
        ]
        if extra_args:
            args.extend(map(str, extra_args))

        self._ever_connected = False
        self._connect_timeout_ms = max(500, int(connect_timeout * 1000))
        self._connect_timer.start(self._connect_timeout_ms)

        self._p.start(sys.executable, args, cwd=str(self._cwd))

    def stop(self, grace_ms: int = 800) -> None:
        """Graceful stop, then terminate/kill as needed."""
        self._connect_timer.stop()
        self._p.send({"cmd": "stop"})
        self._p.stop(grace_ms)

    def isRunning(self) -> bool:
        return self._p.isRunning()

    def pid(self) -> int:
        return self._p.pid()

    # ---------------- commands ----------------

    def request_status(self) -> None:
        self._p.send({"cmd": "status"})

    def set_temp(self, value: float) -> None:
        self._p.send({"cmd": "set_temp", "value": float(value)})

    def power(self, on: bool) -> None:
        # accepts True/False, "on"/"off", 1/0 in the worker
        self._p.send({"cmd": "power", "on": bool(on)})

    # ---------------- routing & finish ----------------

    def _route(self, msg: dict) -> None:
        et = msg.get("event")
        if et == "connected":
            self._ever_connected = True
            self._connect_timer.stop()
            dev = str(msg.get("dev", ""))
            self.connected.emit(dev)
        elif et == "disconnected":
            self.disconnected.emit()
        elif et == "temp":
            try:
                self.temp.emit(float(msg.get("value")))
            except Exception:
                self.warn.emit(f"bad temp payload: {msg}")
        elif et == "status":
            self.status.emit(msg)
        elif et == "ack":
            self.ack.emit(msg)
        elif et == "warn":
            self.warn.emit(str(msg.get("message", "warning")))
            self.log.emit(f"{msg}\n")
        elif et == "error":
            # Surface worker-side error immediately (e.g., port open failure)
            self._connect_timer.stop()
            self.error.emit(str(msg.get("message", "error")))
            self.log.emit(f"{msg}\n")
        else:
            self.log.emit(f"{msg}\n")

    def _on_finished(self, code: int) -> None:
        # If we never got "connected" and the worker exited, tell the UI clearly.
        if not self._ever_connected and code != 0:
            self.error.emit(f"Chiller worker failed to start (exit code {code}).")
        self.disconnected.emit()

    # ---------------- timeouts & errors ----------------

    def _on_connect_timeout(self) -> None:
        if self._ever_connected:
            return
        # No connected event within timeout -> abort and report
        self.error.emit("Chiller connect timed out.")
        self.stop(grace_ms=500)

    def _on_proc_error(self, s: str) -> None:
        self._connect_timer.stop()
        self.error.emit(s)
