import threading
import serial
import time

tester_stop_evt = threading.Event()

# FIX: KCU IP and other things should be in json config?
# Still need to figure out how udev rules will play here
def start_testing():

    tester_stop_evt.clear()
    testing_thread = threading.Thread(target=test, args=(), daemon=True)
    testing_thread.start()

    return testing_thread

def stop_testing(thread):
    tester_stop_evt.set()
    if thread:
        thread.join(timeout=1)


# Still figuring out how to talk to tamalero