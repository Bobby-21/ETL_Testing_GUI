import sys
import os

# Add module_test_sw to python path so tamalero can be imported as a top-level package
sys.path.append(os.path.join(os.path.dirname(__file__), 'module_test_sw'))

from etlup.tamalero import Baseline, Noisewidth
from qaqc import TestSequence
from qaqc.setup_context import SetupContext
from unittest.mock import MagicMock

def main():
    # Define the sequence of tests
    my_tests_sequence = [
        Baseline.BaselineV0,
        Noisewidth.NoisewidthV0
    ]

    # Create the TestSequence object
    test_seq = TestSequence(my_tests_sequence)

    # Mock ReadoutBoard for this example
    mock_rb = MagicMock()

    # Create the context
    context = SetupContext(
        rb=1,
        rb_flavor=3,
        rb_serial_number="RB_001",
        modules={1: "MOD_A", 2: "MOD_B"},
        readout_board=mock_rb,
        room_temp_celcius=25
    )

    previous_results = []

    # Iterate and run each test
    print("Starting test sequence...")
    for t in test_seq:
        print(f"Running test: {t.model}")
        # Pass context and previous_results to the test function
        result = t.run(
            context=context, 
            previous_results=previous_results)
        previous_results.append(result)
        print(f"Test {t.model} completed. Result: {result}")
    
    print("Test sequence completed.")

if __name__ == "__main__":
    main()
