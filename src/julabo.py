# julabo.py
# JSONL-based worker spawned by the GUI with QProcess.
# - Imports JULABO from maindir/drivers/Julabo/julabolib.py (method 1)
# - Receives commands on stdin as JSON lines (also accepts simple text commands)
# - Emits JSON events on stdout (one per line)
# - Polls temperature at --sample_time interval

import sys, json, time, threading, queue, argparse
from pathlib import Path

# ---------- Add project root (maindir) to sys.path, then import ----------
MAIN_DIR = Path(__file__).resolve().parents[1]  
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

from drivers.Julabo.julabolib import JULABO  # maindir/drivers/Julabo/julabolib.py

# ---------- globals ----------
stop_evt = threading.Event()
cmd_q: "queue.Queue[dict|str]" = queue.Queue(maxsize=100)

# ---------- io helpers ----------
def jprint(obj: dict) -> None:
    """Write a JSON event as a single line to stdout (UTF-8)."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def reader_thread():
    """Read stdin lines and enqueue commands (JSON preferred; text allowed)."""
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            cmd_q.put(json.loads(line), timeout=0.1)
        except Exception:
            cmd_q.put(line, timeout=0.1)

# ---------- command handling ----------
def handle_cmd(jb: JULABO, cmd) -> None:
    """
    Execute one command against the JULABO and emit results.
    JSON commands:
      {"cmd":"set_temp","value":23.5}
      {"cmd":"power","on":true}
      {"cmd":"status"}
      {"cmd":"get_temp"}
      {"cmd":"get_setpoint"}
    Also supports plain text:
      set_work_temperature 23.5 | get_temperature | get_work_temperature
      set_power_on | set_power_off | get_power | get_status
    """
    try:
        # ---- plain text form ----
        if isinstance(cmd, str):
            parts = cmd.split()
            if not parts:
                return
            name, args = parts[0], parts[1:]
            if name == "set_work_temperature" and args:
                val = float(args[0])
                jb.set_work_temperature(val)
                jprint({"event": "ack", "cmd": "set_temp", "value": val})
            elif name == "get_temperature":
                pv = jb.get_temperature(); jprint({"event": "temp", "value": pv})
            elif name == "get_work_temperature":
                sp = jb.get_work_temperature(); jprint({"event": "status", "setpoint": sp})
            elif name == "set_power_on":
                jb.set_power_on(); jprint({"event":"ack","cmd":"power","on":True})
            elif name == "set_power_off":
                jb.set_power_off(); jprint({"event":"ack","cmd":"power","on":False})
            elif name == "get_power":
                p = jb.get_power(); jprint({"event":"status","power":p})
            elif name == "get_status":
                st = jb.get_status(); jprint({"event":"status","status_raw":st})
            else:
                jprint({"event":"error","message":f"unknown text cmd: {cmd}"})
            return

        # ---- JSON form ----
        name = str(cmd.get("cmd"))
        if name == "set_temp":
            val = float(cmd["value"])
            jb.set_work_temperature(val)
            jprint({"event": "ack", "cmd": "set_temp", "value": val})

        elif name == "power":
            on = bool(cmd.get("on"))
            if on: jb.set_power_on()
            else:  jb.set_power_off()
            jprint({"event":"ack","cmd":"power","on":on})

        elif name == "status":
            out = {"event":"status"}
            try: out["setpoint"] = jb.get_work_temperature()
            except Exception: pass
            try: out["temperature"] = jb.get_temperature()
            except Exception: pass
            try: out["power"] = jb.get_power()
            except Exception: pass
            jprint(out)

        elif name == "get_temp":
            pv = jb.get_temperature()
            jprint({"event":"temp","value":pv})

        elif name == "get_setpoint":
            sp = jb.get_work_temperature()
            jprint({"event":"status","setpoint":sp})

        else:
            jprint({"event":"error","message":f"unknown cmd: {cmd}"})

    except Exception as ex:
        jprint({"event":"error","message":f"cmd failed: {ex}", "cmd":cmd})

# ---------- main loop ----------
def execute_loop(jb: JULABO, sample_time: float):
    # Initial snapshot
    try: sp = jb.get_work_temperature()
    except Exception: sp = None
    try: pv = jb.get_temperature()
    except Exception: pv = None
    jprint({"event":"status","setpoint":sp,"temperature":pv})

    last_pv = pv
    while not stop_evt.is_set():
        t0 = time.time()

        # Drain commands quickly
        while True:
            try:
                cmd = cmd_q.get_nowait()
            except queue.Empty:
                break
            handle_cmd(jb, cmd)

        # Poll temperature
        try:
            pv = jb.get_temperature()
            if pv != last_pv:
                jprint({"event":"temp","value":pv})
                last_pv = pv
        except Exception as ex:
            jprint({"event":"error","message":f"poll temp failed: {ex}"})

        # Sleep remainder
        dt = time.time() - t0
        time.sleep(max(0.0, sample_time - dt))

# ---------- entry ----------
def main():
    # Ensure UTF-8 streams (best effort)
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--device", required=True, help="Serial device (/dev/ttyUSB0, /dev/cu.*)")
    ap.add_argument("--baud", type=int, default=4800, help="Julabo default baud")
    ap.add_argument("--sample_time", type=float, default=1.0, help="Polling interval (s)")
    args = ap.parse_args()

    try:
        jb = JULABO(args.dev, args.baud)  # julabolib sets 7E1 + RTS/CTS inside
        jprint({"event":"connected","dev":args.dev,"baud":args.baud})
    except Exception as ex:
        jprint({"event":"error","message":f"connect failed: {ex}"})
        return 1

    t = threading.Thread(target=reader_thread, daemon=True)
    t.start()

    rc = 0
    try:
        execute_loop(jb, args.sample_time)
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        jprint({"event":"error","message":f"fatal: {ex}"})
        rc = 3
    finally:
        stop_evt.set()
        try: jb.close()
        except Exception: pass
        jprint({"event":"disconnected"})

    return rc

if __name__ == "__main__":
    sys.exit(main())
