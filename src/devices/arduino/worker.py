# src/devices/arduino/worker.py
from __future__ import annotations

import argparse
import threading
from typing import Any, Dict, Optional

from ...worker_base import BaseWorker
from src.sensors import Sensors  # your existing driver


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/arduino")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--timeout", type=float, default=1.0)          # serial read timeout
    ap.add_argument("--sample_time", type=float, default=1.0)       # telemetry cadence
    ap.add_argument("--connect_timeout", type=float, default=3.0)   # NEW: fail fast if device missing
    return ap.parse_args()


def _connect_with_timeout(dev: Sensors, timeout_s: float) -> Optional[Exception]:
    """
    Attempt dev.connect() on a background thread and join with a timeout.
    Returns an Exception instance if connect raised, None on success.
    If join times out, return TimeoutError().
    """
    err_box: Dict[str, Exception] = {}
    done = threading.Event()

    def _runner():
        try:
            dev.connect()
        except Exception as e:
            err_box["err"] = e
        finally:
            done.set()

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    ok = done.wait(timeout_s)
    if not ok:
        return TimeoutError(f"connect timed out after {timeout_s:.1f}s")
    return err_box.get("err")


def _on_start(w: BaseWorker) -> None:
    args = _parse_args()

    dev = Sensors(args.port, args.baud, args.timeout)

    # ---- attempt connect with timeout ----
    err = _connect_with_timeout(dev, float(args.connect_timeout))
    if err is not None:
        # emit a clear error and exit the worker immediately
        w.emit("error", message=f"Arduino connect failed: {err!r}", port=args.port)
        # raise SystemExit so BaseWorker returns a non-zero exit code
        raise SystemExit(2)

    # store in worker state
    w.state["dev"] = dev
    w.state["sample_time"] = max(0.05, float(args.sample_time))
    w.state["acc"] = 0.0

    w.emit("connected", port=args.port, baud=args.baud)

    # Optional: quick probe to ensure device is responsive
    try:
        dev.update_all()
        payload = dev.package()
        w.emit("data", payload=payload)
    except Exception as e:
        w.emit("error", message=f"Arduino initial read failed: {e!r}")
        raise SystemExit(3)


def _on_tick(w: BaseWorker, dt: float) -> None:
    st = w.state.get("sample_time", 1.0)
    acc = w.state.get("acc", 0.0) + float(dt)
    if acc >= st:
        acc = 0.0
        dev: Sensors = w.state["dev"]
        try:
            dev.update_all()
            payload = dev.package()
            w.emit("data", payload=payload)
        except Exception as e:
            # keep emitting the error and keep running, or choose to exit—here we keep running
            w.emit("error", message=f"Arduino read error: {e!r}")
    w.state["acc"] = acc


def _cmd_status(w: BaseWorker, _msg: Dict[str, Any]) -> None:
    w.emit("status", sample_time=w.state.get("sample_time", 1.0))


def _cmd_set_sample_time(w: BaseWorker, msg: Dict[str, Any]) -> None:
    try:
        st = max(0.05, float(msg.get("value", w.state.get("sample_time", 1.0))))
    except Exception:
        w.emit("warn", message=f"bad set_sample_time value: {msg.get('value')!r}")
        return
    w.state["sample_time"] = st
    w.emit("ack", cmd="set_sample_time", value=st)


def main() -> int:
    worker = BaseWorker(
        on_start=_on_start,
        on_tick=_on_tick,
        period=0.05,
        commands={
            "status": _cmd_status,
            "set_sample_time": _cmd_set_sample_time,
            # "stop" provided by BaseWorker
        },
    )
    return worker.run_forever()


if __name__ == "__main__":
    raise SystemExit(main())
