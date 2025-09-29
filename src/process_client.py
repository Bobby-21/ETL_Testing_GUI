# src/process_client.py
"""
Generic QProcess wrapper for JSON-lines IPC (with plain-text passthrough).

- Start any Python (or non-Python) worker with args and optional extra env.
- Read stdout as a stream of lines:
    * JSON lines -> emitted via `message` (dict)
    * Non-JSON   -> emitted via `textOutput` (str)
- Send JSON commands to the worker via `send({...})`.
- Graceful stop: send your own "stop" command first (if applicable),
  then call `stop(grace_ms)` to terminate() and finally kill() if needed.

This class is intentionally device-agnostic. Device-specific "client"
classes should compose this and implement schema-specific routing.
"""
from __future__ import annotations

import json
from typing import Dict, Iterable, Optional

from PyQt5.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, pyqtSignal


class ProcessClient(QObject):
    # Lifecycle
    started = pyqtSignal()
    finished = pyqtSignal(int)             # exit code
    errorOccurred = pyqtSignal(str)

    # I/O
    textOutput = pyqtSignal(str)           # raw, non-JSON stdout lines
    message = pyqtSignal(dict)             # parsed JSON objects (one per line)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._proc = QProcess(self)

        # Sensible default env for colored output + unbuffered pipes
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("LANG", "en_US.UTF-8")
        env.insert("LC_ALL", "en_US.UTF-8")
        env.insert("TERM", "xterm-256color")
        env.insert("CLICOLOR_FORCE", "1")
        env.insert("FORCE_COLOR", "3")
        self._proc.setProcessEnvironment(env)

        # Merge stderr into stdout; we’ll parse everything line-by-line
        self._proc.setProcessChannelMode(QProcess.MergedChannels)

        # Wire signals
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)
        self._proc.started.connect(self.started.emit)
        self._proc.finished.connect(lambda code, _status: self.finished.emit(code))
        self._proc.errorOccurred.connect(lambda err: self.errorOccurred.emit(str(err)))

        # Internal buffer for partial lines across chunks
        self._buf = ""

    # ---------------------- Public API ----------------------

    def start(
        self,
        cmd: str,
        args: Iterable[str] = (),
        *,
        cwd: Optional[str] = None,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Launch the worker process.

        Parameters
        ----------
        cmd : str
            Executable (e.g., sys.executable) or script path.
        args : Iterable[str]
            Arguments list (do not include `cmd` itself).
        cwd : Optional[str]
            Working directory for the process.
        extra_env : Optional[Dict[str, str]]
            Additional environment overrides for this process.
        """
        if cwd:
            self._proc.setWorkingDirectory(cwd)
        if extra_env:
            env = self._proc.processEnvironment()
            for k, v in extra_env.items():
                env.insert(str(k), str(v))
            self._proc.setProcessEnvironment(env)

        # Reset line buffer when (re)starting
        self._buf = ""
        self._proc.start(cmd, list(args))

    def stop(self, grace_ms: int = 800) -> None:
        """
        Ask the OS to terminate the process; after `grace_ms`, force-kill if needed.
        (Callers should *also* send a JSON {"cmd":"stop"} first, if the worker supports it.)
        """
        if self._proc.state() == QProcess.NotRunning:
            return
        self._proc.terminate()
        QTimer.singleShot(
            int(grace_ms),
            lambda: self._proc.kill() if self._proc.state() != QProcess.NotRunning else None,
        )

    def isRunning(self) -> bool:
        return self._proc.state() != QProcess.NotRunning

    def pid(self) -> int:
        # Q_PID is platform-specific; cast to int safely
        try:
            return int(self._proc.processId() or 0)
        except Exception:
            return 0

    def terminate(self) -> None:
        self._proc.terminate()

    def kill(self) -> None:
        self._proc.kill()

    def state(self) -> QProcess.ProcessState:
        return self._proc.state()

    def send(self, obj: dict) -> None:
        """
        Send a JSON command as one line. No-op if process isn't running.
        """
        if not self.isRunning():
            return
        try:
            data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
            self._proc.write(data)
        except Exception as e:
            self.errorOccurred.emit(f"send failed: {e}")

    def send_text(self, line: str) -> None:
        """
        Send raw text (with trailing newline) to the worker's stdin.
        Useful if your worker expects textual commands instead of JSON.
        """
        if not self.isRunning():
            return
        if not line.endswith("\n"):
            line += "\n"
        try:
            self._proc.write(line.encode("utf-8"))
        except Exception as e:
            self.errorOccurred.emit(f"send_text failed: {e}")

    # ---------------------- Internal ----------------------

    def _on_ready_read(self) -> None:
        """
        Accumulate stdout, split by newline, parse JSON if possible,
        otherwise forward to textOutput.
        """
        try:
            chunk = bytes(self._proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        except Exception as e:
            self.errorOccurred.emit(f"stdout read failed: {e}")
            return

        if not chunk:
            return

        self._buf += chunk
        # Split into complete lines, keep the trailing fragment (if any) in _buf
        *lines, self._buf = self._buf.splitlines(keepends=False)

        for raw in lines:
            s = raw.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                self.textOutput.emit(raw + "\n")
            else:
                # Ensure dict for downstream type safety; other JSON types pass as-is
                if isinstance(obj, dict):
                    self.message.emit(obj)
                else:
                    # Non-dict JSON (array/number/string): forward as message too
                    self.message.emit({"event": "json", "payload": obj})
