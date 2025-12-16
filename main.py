import sys
import os

# Add module_test_sw to python path so tamalero can be imported as a top-level package
sys.path.append(os.path.join(os.path.dirname(__file__), 'module_test_sw'))

from etlup.tamalero import Baseline, Noisewidth, ReadoutBoardCommunication
from qaqc.session import Session

def main():
    # Create the session with configuration
    session = Session(
        rb=0,
        rb_size=3,
        rb_serial_number="RB_001",
        modules=["MOD_A", None, None],
        kcu_ipaddress="192.168.0.10",
        room_temp_celcius=25
    )

    # Define the sequence of tests
    my_tests_sequence = [
        ReadoutBoardCommunication.ReadoutBoardCommunicationV0,
    ]

    # Run the tests
    print("Starting test sequence...")
    for test, result in session.iter_test_sequence(my_tests_sequence, slot=0):
        if isinstance(result, Exception):
            print(f"Test {test.model} failed: {result}")
        else:
            print(f"Test {test.model} passed")
    print("Test sequence completed.")
    print(session.results)

if __name__ == "__main__":
    main()
