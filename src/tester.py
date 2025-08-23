import threading
import subprocess
from pathlib import Path

def run_uv_script(script_path, test_name, kcu_ip, moduleid, qinj, charges):
    if test_name == "tamalero":
        cmd = ["uv", "run", "python3", script_path, "--kcu", kcu_ip, "--power_up"]
        subprocess.run(cmd)
    elif test_name == "module" and qinj == True:
        cmd = ["uv", "run", "python3", script_path, "--kcu", kcu_ip, "--test_chip", "--moduleid", moduleid, "--qinj", "--charges", charges]
        subprocess.run(cmd)
    elif test_name == "module" and qinj == False:
        cmd = ["uv", "run", "python3", script_path, "--kcu", kcu_ip, "--test_chip", "--moduleid", moduleid]
        subprocess.run(cmd)


# KCU IP should be in a config somewhere
def thread_target(test_name, kcu_ip, moduleid, qinj, charges):
    if test_name == "tamalero":
        script_path = Path(__file__).parent.parent / "module_test_sw" / "test_tamalero.py"
        run_uv_script(script_path, test_name, kcu_ip, moduleid, qinj, charges)
    elif test_name == "module":
        script_path = Path(__file__).parent.parent / "module_test_sw" / "test_module.py"
        run_uv_script(script_path, test_name, kcu_ip, moduleid, qinj, charges)

def initiate_test(test_name, kcu_ip, moduleid, qinj=False, charges = [10,20,30]):
    t = threading.Thread(target=thread_target, args=(test_name, kcu_ip, moduleid, qinj, charges), daemon=True)
    t.start()
    t.join()