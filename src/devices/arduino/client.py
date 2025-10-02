# src/devices/arduino/client.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal
from ...process_client import ProcessClient


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


class ArduinoClient(QObject):
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    connected = pyqtSignal(str)     # port
    disconnected = pyqtSignal()
    status = pyqtSignal(dict)
    data = pyqtSignal(dict)
    ack = pyqtSignal(dict)
    warn = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._p = ProcessClient(self)
        self._p.textOutput.connect(self.log.emit)
        self._p.message.connect(self._route)
        self._p.errorOccurred.connect(self.error.emit)
        self._p.finished.connect(self._on_finished)   # NEW: notice early exits

        src_root = _repo_root_from_here() / "src"
        self._worker_path = src_root / "devices" / "arduino" / "worker.py"
        self._cwd = _repo_root_from_here()

        self._ever_connected = False  # NEW: to distinguish early failure

    # ---------- lifecycle ----------

    def start(self, *, port: str = "/dev/arduino", baud: int = 115200,
              timeout: float = 1.0, sample_time: float = 1.0,
              connect_timeout: float = 3.0) -> None:
        args = [
            "-u", str(self._worker_path),
            "--port", str(port),
            "--baud", str(int(baud)),
            "--timeout", str(float(timeout)),
            "--sample_time", str(float(sample_time)),
            "--connect_timeout", str(float(connect_timeout)),
        ]
        self._ever_connected = False
        self._p.start(sys.executable, args, cwd=str(self._cwd))

    def stop(self, grace_ms: int = 800) -> None:
        self._p.send({"cmd": "stop"})
        self._p.stop(grace_ms)

    def isRunning(self) -> bool:
        return self._p.isRunning()

    def pid(self) -> int:
        return self._p.pid()

    # ---------- commands ----------

    def set_sample_time(self, value: float) -> None:
        self._p.send({"cmd": "set_sample_time", "value": float(value)})

    def request_status(self) -> None:
        self._p.send({"cmd": "status"})

    # ---------- routing & finish ----------

    def _route(self, msg: dict) -> None:
        et = msg.get("event")
        if et == "connected":
            self._ever_connected = True
            self.connected.emit(str(msg.get("port", "")))
        elif et == "disconnected":
            self.disconnected.emit()
        elif et == "status":
            self.status.emit(msg)
        elif et == "data":
            self.data.emit(msg.get("payload") or {})
        elif et == "ack":
            self.ack.emit(msg)
        elif et == "warn":
            self.warn.emit(str(msg.get("message", "warning")))
            self.log.emit(f"{msg}\n")
        elif et == "error":
            # Surface worker-side error immediately (e.g., connect timeout)
            self.error.emit(str(msg.get("message", "error")))
            self.log.emit(f"{msg}\n")
        else:
            self.log.emit(f"{msg}\n")

    def _on_finished(self, code: int) -> None:
        # If we never got "connected" and the worker exited, tell the UI clearly.
        if not self._ever_connected and code != 0:
            self.error.emit(f"Arduino worker failed to start (exit code {code}).")
        # Always notify disconnection so UI can reset buttons.
        self.disconnected.emit()
