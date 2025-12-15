import sys
import os

# Add module_test_sw to python path so tamalero can be imported as a top-level package
sys.path.append(os.path.join(os.path.dirname(__file__), 'module_test_sw'))

from etlup.tamalero import Baseline, Noisewidth
from qaqc.session import Session
from qaqc.test_runner import TestRunner

def main():
    # Create the session with configuration
    session = Session(
        rb=1,
        rb_size=3,
        rb_serial_number="RB_001",
        modules=["MOD_A", None, "MOD_B"],
        kcu_ipaddress="192.168.0.10",
        room_temp_celcius=25
    )
    # Initialize TestRunner with the session
    runner = TestRunner(session)

    # Define the sequence of tests
    my_tests_sequence = [
        "ReadoutBoardConnectionV0",
        Baseline.BaselineV0,
        Noisewidth.NoisewidthV0
    ]

    # Run the tests
    print("Starting test sequence...")
    runner.run_test_sequence(my_tests_sequence, slot=0)
    print("Test sequence completed.")

if __name__ == "__main__":
    main()
