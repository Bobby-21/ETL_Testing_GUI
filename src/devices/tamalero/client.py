# src/devices/tamalero/client.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from ...process_client import ProcessClient


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


class TamaleroClient(QObject):
    """
    Qt client wrapper around the tamalero worker.

    Signals
    -------
    log(str):             passthrough of raw stdout from child scripts
    error(str), warn(str)
    ready():              worker is up and ready to accept commands
    disconnected()
    conn_started(dict):   args used for connection launch
    conn_finished(int):   exit code
    test_started(dict):   args used for module test launch
    test_finished(int):   exit code
    status(dict):         {"conn_running":bool,"test_running":bool}

    Methods
    -------
    start(), stop()
    connect_kcu(kcu, verbose=True, power_up=True, adcs=True)
    run_module(configuration, kcu, host, moduleid, module, qinj=False, charges=None, nl1a=None)
    abort()
    request_status()
    """

    # lifecycle/logging
    ready = pyqtSignal()
    disconnected = pyqtSignal()
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    warn = pyqtSignal(str)

    # child lifecycle
    conn_started = pyqtSignal(dict)
    conn_finished = pyqtSignal(int)
    test_started = pyqtSignal(dict)
    test_finished = pyqtSignal(int)

    status = pyqtSignal(dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._p = ProcessClient(self)
        self._p.textOutput.connect(self.log.emit)
        self._p.message.connect(self._route)
        self._p.errorOccurred.connect(self._on_proc_error)
        self._p.finished.connect(self._on_finished)

        root = _repo_root_from_here()
        self._cwd = root
        self._worker_path = root / "src" / "devices" / "tamalero" / "worker.py"

        # optional connect-time watchdog (if worker never becomes 'ready')
        self._start_timer = QTimer(self)
        self._start_timer.setSingleShot(True)
        self._start_timer.timeout.connect(self._on_start_timeout)
        self._start_timeout_ms = 4000

        self._seen_ready = False

    # ---------- lifecycle ----------

    def start(self, start_timeout: float = 4.0) -> None:
        """Start the worker process; it will wait for commands."""
        args = ["-u", str(self._worker_path)]
        # self._seen_ready = False
        # self._start_timeout_ms = 30000
        # self._start_timer.start(self._start_timeout_ms)
        self._p.start(sys.executable, args, cwd=str(self._cwd))

    def stop(self, grace_ms: int = 800) -> None:
        # self._start_timer.stop()
        self._p.send({"cmd": "stop"})
        self._p.stop(grace_ms)

    def isRunning(self) -> bool:
        return self._p.isRunning()

    # ---------- commands ----------

    def connect_kcu(self, *, kcu: str, verbose: bool = True, power_up: bool = True, adcs: bool = True) -> None:
        self._p.send({"cmd": "connect", "kcu": kcu, "verbose": bool(verbose), "power_up": bool(power_up), "adcs": bool(adcs)})

    def run_module(
        self, *,
        configuration: str,
        kcu: str,
        host: str,
        moduleid: str,
        module: str = "1",
        qinj: bool = False,
        charges: Optional[Sequence[str]] = None,
        nl1a: Optional[str] = None,
    ) -> None:
        payload = {
            "cmd": "run_module",
            "configuration": configuration,
            "kcu": kcu,
            "host": host,
            "moduleid": moduleid,
            "module": module,
            "qinj": bool(qinj),
            "charges": list(charges) if charges else [],
        }
        if nl1a:
            payload["nl1a"] = str(nl1a)
        self._p.send(payload)

    def abort(self) -> None:
        self._p.send({"cmd": "abort"})

    def request_status(self) -> None:
        self._p.send({"cmd": "status"})

    # ---------- routing ----------

    def _route(self, msg: dict) -> None:
        et = msg.get("event")
        if et == "ready":
            self._seen_ready = True
            #self._start_timer.stop()
            self.ready.emit()
        elif et == "status":
            self.status.emit(msg)
        elif et == "conn_started":
            self.conn_started.emit(msg.get("args") or {})
        elif et == "conn_finished":
            try:
                self.conn_finished.emit(int(msg.get("code", 0)))
            except Exception:
                self.conn_finished.emit(-1)
        elif et == "test_started":
            self.test_started.emit(msg.get("args") or {})
        elif et == "test_finished":
            try:
                self.test_finished.emit(int(msg.get("code", 0)))
            except Exception:
                self.test_finished.emit(-1)
        elif et == "warn":
            self.warn.emit(str(msg.get("message", "warning")))
            self.log.emit(f"{msg}\n")
        elif et == "error":
            self.error.emit(str(msg.get("message", "error")))
            self.log.emit(f"{msg}\n")
        else:
            # unknown JSON -> log for visibility
            self.log.emit(f"{msg}\n")

    def _on_finished(self, _code: int) -> None:
        self.disconnected.emit()

    def _on_proc_error(self, s: str) -> None:
        self.error.emit(s)

    def _on_start_timeout(self) -> None:
        if self._seen_ready:
            return
        self.error.emit("Tamalero worker failed to become ready.")
        self.stop(grace_ms=500)
