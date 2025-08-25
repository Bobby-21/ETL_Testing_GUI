import threading
import serial
import time
import queue
from sensors import Sensors

data_q = queue.Queue(maxsize=10)
recorder_stop_evt = threading.Event()

# FIX: Sensors object should be initialized with values from json config
# Still need to figure out how udev rules will play here
def start_recording(port, baud=115200, timeout=1.0, sample_time=1.0):
    arduino = Sensors(port, baud, timeout)
    try:
        arduino.connect()
    except serial.SerialException as e:
        print(f"Failed to connect: {e}")
        return False, None, arduino

    recorder_stop_evt.clear()
    recording_thread = threading.Thread(target=record, args=(arduino, sample_time), daemon=True)
    recording_thread.start()

    return arduino.check_serial_connected(), recording_thread, arduino

def stop_recording(thread, arduino):
    recorder_stop_evt.set()
    if thread:
        thread.join(timeout=1)
    if arduino:
        arduino.close()


def record(ard, sample_time):
    while not recorder_stop_evt.is_set():

        try:
            ard.update_all()
            data = ard.package()
        except Exception as e:
            print(f"Recording Error: {e}")

        if not data_q.empty():
            data_q.get_nowait()
        data_q.put_nowait(data)

        time.sleep(sample_time)