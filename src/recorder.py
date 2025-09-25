import threading
import serial
import time
import queue
from sensors import Sensors

# FIX: Sensors object should be initialized with values from json config
def start_recording(port="/dev/arduino", baud=115200, timeout=1.0, sample_time=1.0):

    data_q = queue.Queue(maxsize=10)
    recorder_stop_evt = threading.Event()

    arduino = Sensors(port, baud, timeout)
    try:
        arduino.connect()
    except serial.SerialException as e:
        print(f"Failed to connect: {e}")
        return False, None, arduino

    recorder_stop_evt.clear()
    recording_thread = threading.Thread(target=record, args=(arduino, sample_time, data_q, recorder_stop_evt), daemon=True)
    recording_thread.start()

    return arduino.check_serial_connected(), recording_thread, arduino, recorder_stop_evt, data_q

def stop_recording(thread, arduino, stop_evt):
    stop_evt.set()
    if thread:
        thread.join(timeout=1)
    if arduino:
        arduino.close()


def record(ard, sample_time, dqueue, stop_evt):
    while not stop_evt.is_set():

        try:
            ard.update_all()
            data = ard.package()
        except Exception as e:
            print(f"Recording Error: {e}")

        if not dqueue.empty():
            dqueue.get_nowait()
        dqueue.put_nowait(data)

        time.sleep(sample_time)