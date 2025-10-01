# src/worker_base.py
"""
Tiny utilities to build robust JSON-lines workers.

Usage pattern
-------------
from worker_base import BaseWorker

def on_start(w: BaseWorker):
    # Construct your driver here, stash in w.state
    # e.g., w.state["dev"] = MyDriver(...)
    pass

def on_tick(w: BaseWorker, dt: float):
    # Periodic polling / telemetry emission
    # e.g., val = w.state["dev"].read()
    #       w.emit("data", value=val)
    pass

def cmd_setpoint(w: BaseWorker, msg: dict):
    sp = float(msg.get("value", 0.0))
    # w.state["dev"].setpoint(sp)
    w.emit("ack", cmd="setpoint", value=sp)

worker = BaseWorker(
    on_start=on_start,
    on_tick=on_tick,
    period=0.1,
    commands={"setpoint": cmd_setpoint},
)
worker.run_forever()

Design goals
------------
- Device-agnostic: no Qt, no drivers imported here.
- Resilient: exceptions are captured and reported as JSON events.
- Cooperative shutdown:
  * Accepts {"cmd":"stop"} by default
  * Detects stdin EOF and exits cleanly
- Non-blocking stdin using selectors; periodic tick function with consistent cadence.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
import selectors
from typing import Callable, Dict, Optional, Any


def jsonl_write(obj: dict) -> None:
    """Write a single JSON object as a line to stdout (UTF-8), flush immediately."""
    try:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        # Last-resort: avoid crashing the worker because output failed
        try:
            sys.stdout.write('{"event":"error","message":"failed to write json"}\n')
            sys.stdout.flush()
        except Exception:
            pass


class BaseWorker:
    """
    Minimal event-loop to build JSONL workers.

    Parameters
    ----------
    on_start : Callable[[BaseWorker], None]
        Called once before entering the loop. Construct your driver here.
    on_tick : Optional[Callable[[BaseWorker, float], None]]
        Periodic callback; receives dt (seconds) since last call.
    period : float
        Desired tick interval in seconds (>= 0.01 recommended).
    commands : Dict[str, Callable[[BaseWorker, dict], None]]
        Map command names to handlers. Each handler receives (worker, msg_dict).
        A default "stop" command is provided unless you override it.
    """

    def __init__(
        self,
        *,
        on_start: Callable[["BaseWorker"], None],
        on_tick: Optional[Callable[["BaseWorker", float], None]] = None,
        period: float = 0.1,
        commands: Optional[Dict[str, Callable[["BaseWorker", dict], None]]] = None,
    ) -> None:
        self.on_start = on_start
        self.on_tick = on_tick
        self.period = max(0.01, float(period))
        self.commands = dict(commands or {})
        self.state: Dict[str, Any] = {}

        # Built-in "stop" command if not overridden
        self.commands.setdefault("stop", lambda w, _m: w._request_stop())

        # IO
        self._sel = selectors.DefaultSelector()
        self._running = False

    # ---------- Convenience ----------

    def emit(self, event: str, **payload: Any) -> None:
        """Emit a typed event to stdout as JSON."""
        msg = {"event": event}
        msg.update(payload)
        jsonl_write(msg)

    # ---------- Loop & command handling ----------

    def run_forever(self) -> int:
        """
        Run the worker loop until:
        - a {"cmd":"stop"} is received,
        - stdin closes (EOF),
        - or an unhandled exception occurs (reported via "error" event).
        Returns the intended exit code (0 on clean stop, 2+ on error).
        """
        exit_code = 0
        try:
            # Prepare stdin for non-blocking line reads
            self._sel.register(sys.stdin, selectors.EVENT_READ)
            self._running = True

            # Startup hook
            try:
                self.on_start(self)
            except SystemExit:
                raise
            except Exception:
                self.emit("error", message="startup failed", trace=traceback.format_exc())
                return 2

            # Main loop
            last_tick = time.perf_counter()
            while self._running:
                # 1) Poll commands with small timeout to honor tick cadence
                timeout = max(0.0, self.period * 0.5)
                for _key, _mask in self._sel.select(timeout=timeout):
                    line = sys.stdin.readline()
                    if not line:
                        # stdin EOF -> peer closed -> graceful shutdown
                        self.emit("disconnected")
                        self._running = False
                        break
                    self._dispatch_cmd(line)

                # 2) Tick (if provided)
                now = time.perf_counter()
                dt = now - last_tick
                if dt >= self.period and self.on_tick:
                    try:
                        self.on_tick(self, dt)
                    except SystemExit:
                        raise
                    except Exception:
                        self.emit("error", message="tick failed", trace=traceback.format_exc())
                    last_tick = now

            # Clean stop
            return exit_code

        except SystemExit as ex:
            return int(getattr(ex, "code", 0) or 0)
        except Exception:
            self.emit("error", message="worker crashed", trace=traceback.format_exc())
            return 3
        finally:
            # Allow device teardown without crashing the loop
            try:
                self._teardown()
            except Exception:
                self.emit("warn", message="teardown failed", trace=traceback.format_exc())

    def _dispatch_cmd(self, line: str) -> None:
        s = line.strip()
        if not s:
            return
        try:
            msg = json.loads(s)
        except Exception:
            self.emit("warn", message=f"bad json: {s[:200]}...")
            return

        cmd = (msg.get("cmd") or "").strip().lower()
        handler = self.commands.get(cmd)
        if not handler:
            self.emit("warn", message=f"unknown cmd: {cmd}")
            return

        try:
            handler(self, msg)
        except SystemExit:
            raise
        except Exception:
            self.emit("error", message=f"command '{cmd}' failed", trace=traceback.format_exc())

    def _request_stop(self) -> None:
        """Default stop handler."""
        self.emit("ack", cmd="stop")
        self._running = False

    # ---------- Teardown hook ----------

    def _teardown(self) -> None:
        """
        Override in subclasses or close things added to `self.state` in on_start.
        Called once when the loop ends (cleanly or due to error).
        """
        dev = self.state.get("dev")
        if dev is not None:
            try:
                close = getattr(dev, "close", None)
                if callable(close):
                    close()
            except Exception:
                self.emit("warn", message="device close failed", trace=traceback.format_exc())
