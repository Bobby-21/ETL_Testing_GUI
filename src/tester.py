import threading
import subprocess
from pathlib import Path

class JobHandle:
    """Handle for a running job: lets you stop it and check if alive."""
    def __init__(self, thread, stop_event, holder):
        self.thread = thread
        self._stop_event = stop_event
        self._holder = holder  # {"popen": Popen or None}

    def stop(self):
        """Signal the reader thread to stop and terminate the process if still running."""
        self._stop_event.set()
        popen = self._holder.get("popen")
        if popen and popen.poll() is None:
            try:
                popen.terminate()
            except Exception:
                pass

    def is_running(self):
        return self.thread.is_alive()


def _truthy(x):
    """Treat many values as 'true' without forcing types."""
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    return s in ("1", "true", "yes", "y", "on")


def _normalize_charges(charges):
    """
    Accept '[10,20,30]', '10 20 30', '10,20,30', ['10','20','30'], (10,20,30), etc.
    Return a flat list of strings: ['10','20','30'].
    """
    if charges is None:
        return []
    if isinstance(charges, str):
        s = charges.strip().strip("[]")
        if not s:
            return []
        parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
        return parts
    # assume iterable
    try:
        return [str(x) for x in charges]
    except Exception:
        return [str(charges)]


def _build_cmd(script_path, test_name, kcu_ip, moduleid, qinj, charges):
    # Base: uv run python3 <script> --kcu <ip>
    cmd = ["uv", "run", "python3", str(script_path), "--kcu", str(kcu_ip)]

    if test_name == "tamalero":
        # Match your typical flags (adjust as needed)
        cmd += ["--power_up", "--adcs", "--verbose"]

    elif test_name == "module":
        cmd += ["--test_chip"]
        if moduleid not in (None, ""):
            cmd += ["--moduleid", str(moduleid)]
        if _truthy(qinj):
            cmd += ["--qinj"]
            ch_list = _normalize_charges(charges)
            if ch_list:
                cmd += ["--charges", *ch_list]

    else:
        raise ValueError("Unknown test_name: %r" % test_name)

    return cmd


def run_uv_script(script_path, test_name, kcu_ip, moduleid, qinj, charges,
                  on_output, stop_event, holder):
    """
    Launch the UV+python command and stream output lines to on_output(line) if provided.
    """
    cmd = _build_cmd(script_path, test_name, kcu_ip, moduleid, qinj, charges)

    try:
        popen = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        holder["popen"] = popen
    except Exception as e:
        if on_output:
            on_output(f"[tester] Failed to start process: {e}")
        return

    try:
        for line in popen.stdout:
            if stop_event.is_set():
                break
            if on_output:
                on_output(line.rstrip("\n"))
    finally:
        # If we asked to stop and process is still alive, terminate it
        if stop_event.is_set() and popen.poll() is None:
            try:
                popen.terminate()
            except Exception:
                pass
        # Drain any remaining output (best effort)
        try:
            rest = popen.stdout.read()
            if rest and on_output:
                for ln in rest.splitlines():
                    on_output(ln)
        except Exception:
            pass


def thread_target(test_name, kcu_ip, moduleid, qinj, charges, on_output, stop_event, holder):
    # test_<name>.py expected under ../module_test_sw/
    script_path = Path(__file__).parent.parent / "module_test_sw" / f"test_{test_name}.py"
    run_uv_script(script_path, test_name, kcu_ip, moduleid, qinj, charges, on_output, stop_event, holder)


def initiate_test(test_name, kcu_ip, moduleid,
                  qinj=False,
                  charges=(10, 20, 30),
                  on_output=None,
                  join=False):
    """
    Start the test in a background thread and stream output to on_output(line).
    Returns a JobHandle you can stop later.

    Args are purposely untyped/permissive:
      - test_name: "tamalero" or "module"
      - kcu_ip: e.g. '192.168.0.11'
      - moduleid: any value; only used for "module"
      - qinj: truthy → add --qinj (True/'True'/'yes'/1/etc.)
      - charges: string or iterable → '--charges <...>'
      - on_output: callable(line) or None
    """
    stop_event = threading.Event()
    holder = {"popen": None}
    t = threading.Thread(
        target=thread_target,
        args=(test_name, kcu_ip, moduleid, qinj, charges, on_output, stop_event, holder),
        daemon=True,
    )
    t.start()
    handle = JobHandle(t, stop_event, holder)
    if join:
        t.join()
    return handle
