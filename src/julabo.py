import threading
import serial
import time
import queue
from ..drivers.Julabo.julabolib.julabolib import JULABO

chiller_stop_evt = threading.Event()
chiller_cmd_q = queue.Queue(maxsize=10)


def open_julabo_communication(port, baud=4800, sample_time = 1.0):
    chiller = JULABO(port, baud)

    chiller_stop_evt.clear()
    chiller_thread = threading.Thread(target=execute_command, args=(chiller, cmd_q, sample_time), daemon=True)
    chiller_thread.start()

    return chiller.get_status(), chiller_thread, chiller

def stop_julabo_communication(thread, jul):
    chiller_stop_evt.set()
    if thread:
        thread.join(timeout=1)
    if jul:
        jul.close()


def execute_command(jul: JULABO, cmd_queue, sample_time):
    while not chiller_stop_evt.is_set():
        try:
            cmd = cmd_queue.get(timeout=0.1)
            if cmd == 'get_status':
                resp = jul.get_status()
                return resp
            # Command must be 'set_temp float'
            elif cmd.split()[0] == 'set_work_temperature':
                jul.set_work_temperature(float(cmd.split()[1]))
            elif cmd == 'get_work_temperature':
                resp = jul.get_work_temperature()
                return resp
            elif cmd == 'set_power_on':
                jul.set_power_on()
            elif cmd == 'set_power_off':
                jul.set_power_off()
            elif cmd == 'get_power':
                resp = jul.get_power()
                return resp
            elif cmd == 'get_temperature':
                resp = jul.get_temperature()
                return resp
        except Exception as e:
            print(f"Communication error: {e}")

        time.sleep(sample_time)