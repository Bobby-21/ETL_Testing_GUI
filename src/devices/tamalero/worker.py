# src/devices/tamalero/worker.py
from __future__ import annotations

"""
Tamalero worker:
- Long-running JSONL worker that launches two external scripts:
    1) module_test_sw/test_tamalero.py  (the "connection" step)
    2) module_test_sw/test_module.py    (the "module test")
- Forwards each script's stdout to our stdout as *raw text* (non-JSON).
  The GUI ProcessClient will surface these lines via `textOutput -> client.log`.
- Emits small JSON events for lifecycle:
    {"event":"conn_started", "args":{...}}
    {"event":"conn_finished","code":int}
    {"event":"test_started", "args":{...}}
    {"event":"test_finished","code":int}
    {"event":"status", "conn_running":bool, "test_running":bool}
    {"event":"warn"/"error","message":str}

Commands accepted on stdin (JSON per line):
    {"cmd":"connect", "kcu":str, "verbose":bool, "power_up":bool, "adcs":bool}
    {"cmd":"run_module", "configuration":str, "kcu":str, "host":str,
                         "moduleid":str, "module":str,
                         "qinj":bool, "charges":[...], "nl1a":str|null}
    {"cmd":"abort"}
    {"cmd":"status"}
    {"cmd":"stop"}

Notes
-----
- We *do not* import or depend on PyQt here.
- We use threads to read child stdout without blocking the worker loop.
"""

import json
import os
import sys
import time
import shlex
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Iterable, Optional

# ------------- small JSONL helpers -------------

def _jsonl(obj: Dict[str, Any]) -> None:
    try:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        # last resort—don't crash the worker because of a write error
        pass


def _writeln(line: str) -> None:
    """Forward raw text (non-JSON) to stdout for GUI log sink."""
    try:
        if not line.endswith("\n"):
            line += "\n"
        sys.stdout.write(line)
        sys.stdout.flush()
    except Exception:
        pass


# ------------- repo root helper -------------

def _repo_root_from_here() -> Path:
    # this file: <repo>/src/devices/tamalero/worker.py
    return Path(__file__).resolve().parents[3]


# ------------- process I/O helpers -------------

def _reader_thread(proc: subprocess.Popen, tag: str, stop_evt: threading.Event) -> None:
    """
    Read stdout of `proc` line-by-line and forward to GUI as raw text.
    Prefix with a small tag so logs are distinguishable.
    """
    try:
        for raw in iter(proc.stdout.readline, ""):
            if stop_evt.is_set():
                break
            if not raw:
                break
            # Keep the log 'plain' so GUI treats it as textOutput
            _writeln(f"[tamalero:{tag}] {raw.rstrip()}")
    except Exception as e:
        _jsonl({"event": "warn", "message": f"log reader failed ({tag}): {e!r}"})


def _spawn(
    cmd: Iterable[str],
    cwd: Path,
) -> subprocess.Popen:
    """
    Spawn a child script with combined stdout/stderr (text mode, line-buffered).
    """
    return subprocess.Popen(
        list(cmd),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )


# ------------- worker core -------------

class TamaleroWorker:
    def __init__(self) -> None:
        self.repo_root = _repo_root_from_here()
        self.module_dir = self.repo_root / "module_test_sw"

        # child process handles
        self.conn_proc: Optional[subprocess.Popen] = None
        self.test_proc: Optional[subprocess.Popen] = None

        # stdout reader threads + stop flags
        self._conn_reader: Optional[threading.Thread] = None
        self._test_reader: Optional[threading.Thread] = None
        self._conn_stop = threading.Event()
        self._test_stop = threading.Event()

        # loop control
        self._running = True

    # ---------- lifecycle / cleanup ----------

    def _teardown(self) -> None:
        self._terminate("conn", self.conn_proc, self._conn_stop)
        self._terminate("test", self.test_proc, self._test_stop)

    def _terminate(self, tag: str, proc: Optional[subprocess.Popen], stop_evt: threading.Event, grace: float = 0.8) -> None:
        if not proc:
            return
        try:
            stop_evt.set()
            if proc.poll() is None:
                proc.terminate()
                t0 = time.time()
                while proc.poll() is None and (time.time() - t0) < grace:
                    time.sleep(0.05)
            if proc.poll() is None:
                proc.kill()
        except Exception as e:
            _jsonl({"event": "warn", "message": f"terminate {tag} failed: {e!r}"})

    # ---------- commands ----------

    def cmd_connect(self, msg: Dict[str, Any]) -> None:
        if self.conn_proc and (self.conn_proc.poll() is None):
            _jsonl({"event": "warn", "message": "connect already running"})
            return

        kcu = str(msg.get("kcu", "")).strip()
        if not kcu:
            _jsonl({"event": "error", "message": "missing 'kcu' ip"})
            return

        verbose = bool(msg.get("verbose", True))
        power_up = bool(msg.get("power_up", True))
        adcs = bool(msg.get("adcs", True))

        cmd = [
            sys.executable, "-u",
            str(self.module_dir / "test_tamalero.py"),
            "--kcu", kcu,
        ]
        if verbose:
            cmd.append("--verbose")
        if power_up:
            cmd.append("--power_up")
        if adcs:
            cmd.append("--adcs")

        try:
            self._conn_stop.clear()
            self.conn_proc = _spawn(cmd, cwd=self.repo_root)
            self._conn_reader = threading.Thread(
                target=_reader_thread, args=(self.conn_proc, "conn", self._conn_stop), daemon=True
            )
            self._conn_reader.start()
            _jsonl({"event": "conn_started", "args": {"kcu": kcu, "verbose": verbose, "power_up": power_up, "adcs": adcs}})
        except Exception as e:
            _jsonl({"event": "error", "message": f"failed to start connection: {e!r}"})
            return

    def cmd_run_module(self, msg: Dict[str, Any]) -> None:
        if self.test_proc and (self.test_proc.poll() is None):
            _jsonl({"event": "warn", "message": "module test already running"})
            return

        # Required / optional parameters (mirror your panel)
        configuration = str(msg.get("configuration", "modulev2"))
        kcu = str(msg.get("kcu", "")).strip()
        host = str(msg.get("host", "localhost"))
        moduleid = str(msg.get("moduleid", "")).strip()
        module = str(msg.get("module", "1")).strip()
        qinj = bool(msg.get("qinj", False))
        charges = msg.get("charges") or []
        nl1a = msg.get("nl1a", "")

        if not kcu or not moduleid:
            _jsonl({"event": "error", "message": "missing 'kcu' or 'moduleid'"})
            return

        cmd = [
            sys.executable, "-u",
            str(self.module_dir / "test_module.py"),
            "--configuration", configuration,
            "--kcu", kcu,
            "--host", host,
            "--moduleid", moduleid,
            "--test_chip",
            "--module", module,
        ]
        if qinj:
            cmd.append("--qinj")
            if charges:
                # normalize items to strings
                cmd.extend(["--charges", *[str(c) for c in charges]])
        if nl1a:
            cmd.extend(["--nl1a", str(nl1a)])

        try:
            self._test_stop.clear()
            self.test_proc = _spawn(cmd, cwd=self.repo_root)
            self._test_reader = threading.Thread(
                target=_reader_thread, args=(self.test_proc, "test", self._test_stop), daemon=True
            )
            self._test_reader.start()
            _jsonl({"event": "test_started", "args": {
                "configuration": configuration, "kcu": kcu, "host": host,
                "moduleid": moduleid, "module": module, "qinj": qinj,
                "charges": charges, "nl1a": nl1a
            }})
        except Exception as e:
            _jsonl({"event": "error", "message": f"failed to start module test: {e!r}"})
            return

    def cmd_abort(self, _msg: Dict[str, Any]) -> None:
        any_running = False
        if self.conn_proc and (self.conn_proc.poll() is None):
            any_running = True
            _jsonl({"event": "warn", "message": "aborting connection process"})
            self._terminate("conn", self.conn_proc, self._conn_stop)
        if self.test_proc and (self.test_proc.poll() is None):
            any_running = True
            _jsonl({"event": "warn", "message": "aborting test process"})
            self._terminate("test", self.test_proc, self._test_stop)
        if not any_running:
            _jsonl({"event": "warn", "message": "no active tamalero process to abort"})

    def cmd_status(self, _msg: Dict[str, Any]) -> None:
        _jsonl({
            "event": "status",
            "conn_running": bool(self.conn_proc and self.conn_proc.poll() is None),
            "test_running": bool(self.test_proc and self.test_proc.poll() is None),
        })

    def cmd_stop(self, _msg: Dict[str, Any]) -> None:
        _jsonl({"event": "ack", "cmd": "stop"})
        self._running = False

    # ---------- loop ----------

    def _poll_children(self) -> None:
        # Check connection script exit
        if self.conn_proc and (self.conn_proc.poll() is not None):
            code = int(self.conn_proc.returncode or 0)
            _jsonl({"event": "conn_finished", "code": code})
            self._terminate("conn", self.conn_proc, self._conn_stop)
            self.conn_proc = None

        # Check test script exit
        if self.test_proc and (self.test_proc.poll() is not None):
            code = int(self.test_proc.returncode or 0)
            _jsonl({"event": "test_finished", "code": code})
            self._terminate("test", self.test_proc, self._test_stop)
            self.test_proc = None

    def run(self) -> int:
        """
        Simple line-oriented command loop (no selectors to keep it tiny).
        """
        try:
            _jsonl({"event": "ready"})
            while self._running:
                # 1) poll children
                self._poll_children()

                # 2) process a command line if available (non-blocking-ish)
                if sys.stdin in select_readable(0.1):
                    line = sys.stdin.readline()
                    if not line:
                        # stdin closed -> exit
                        break
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        msg = json.loads(s)
                    except Exception:
                        _jsonl({"event": "warn", "message": f"bad json: {s[:200]}..."})
                        continue
                    cmd = (msg.get("cmd") or "").strip().lower()
                    try:
                        if cmd == "connect":
                            self.cmd_connect(msg)
                        elif cmd == "run_module":
                            self.cmd_run_module(msg)
                        elif cmd == "abort":
                            self.cmd_abort(msg)
                        elif cmd == "status":
                            self.cmd_status(msg)
                        elif cmd == "stop":
                            self.cmd_stop(msg)
                        else:
                            _jsonl({"event": "warn", "message": f"unknown cmd: {cmd}"})
                    except Exception as e:
                        _jsonl({"event": "error", "message": f"cmd '{cmd}' failed: {e!r}"})
                else:
                    # small idle sleep to keep CPU low
                    time.sleep(0.02)
            return 0
        finally:
            self._teardown()


# ----- small cross-platform readiness check -----

def select_readable(timeout: float):
    """Return [sys.stdin] if there's data to read within timeout seconds; else []."""
    try:
        import selectors, sys as _sys, time as _time
        sel = selectors.DefaultSelector()
        sel.register(_sys.stdin, selectors.EVENT_READ)
        events = sel.select(timeout)
        sel.close()
        return [_sys.stdin] if events else []
    except Exception:
        # Fallback: crude sleep; will behave as polling
        time.sleep(timeout)
        return []


def main() -> int:
    w = TamaleroWorker()
    return w.run()


if __name__ == "__main__":
    raise SystemExit(main())
