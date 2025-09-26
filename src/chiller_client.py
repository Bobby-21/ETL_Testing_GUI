# src/chiller_client.py
import sys
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal
from .process_client import ProcessClient

MAIN_DIR = Path(__file__).resolve().parents[1]
WORKER_PATH = MAIN_DIR / "src" / "julabo.py"

class ChillerClient(QObject):
    """Thin facade over ProcessClient with convenience methods."""
    connected = pyqtSignal(str)       # device path
    disconnected = pyqtSignal()
    status = pyqtSignal(dict)         # {"setpoint":..., "temperature":..., "power":...}
    temperature = pyqtSignal(float)
    ack = pyqtSignal(dict)
    warn = pyqtSignal(dict)
    error = pyqtSignal(str)
    text = pyqtSignal(str)            # raw non-JSON logs

    def __init__(self, parent=None):
        super().__init__(parent)
        self.p = ProcessClient(self)
        self.p.started.connect(lambda: self.text.emit("[Chiller] worker started\n"))
        self.p.finished.connect(lambda code: self.text.emit(f"[Chiller] worker exited code={code}\n"))
        self.p.errorOccurred.connect(lambda e: self.error.emit(e))
        self.p.textOutput.connect(self.text.emit)
        self.p.message.connect(self._route)

    # ---- lifecycle ----
    def start(self, device: str, sample_time: float = 1.0):
        args = ["-u", str(WORKER_PATH), "--device", device, "--sample_time", str(sample_time)]
        self.p.start(sys.executable, args, cwd=str(MAIN_DIR))

    def stop(self):
        self.p.stop()

    def isRunning(self) -> bool:
        return self.p.isRunning()

    # ---- commands ----
    def set_temp(self, value: float):
        self.p.send({"cmd": "set_temp", "value": float(value)})

    def power(self, on: bool):
        self.p.send({"cmd": "power", "on": bool(on)})

    def request_status(self):
        self.p.send({"cmd": "status"})

    # ---- message router ----
    def _route(self, msg: dict):
        et = msg.get("event")
        if et == "connected":
            self.connected.emit(msg.get("dev",""))
        elif et == "disconnected":
            self.disconnected.emit()
        elif et == "temp":
            try: self.temperature.emit(float(msg.get("value")))
            except Exception: pass
        elif et == "status":
            self.status.emit(msg)
        elif et == "ack":
            self.ack.emit(msg)
        elif et == "warn":
            self.warn.emit(msg)
        elif et == "error":
            self.error.emit(msg.get("message","unknown error"))
        else:
            # forward any unknown messages to text log
            self.text.emit(f"[Chiller] {msg}\n")
