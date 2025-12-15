import sys
import os

# Add module_test_sw to python path so tamalero can be imported as a top-level package
sys.path.append(os.path.join(os.path.dirname(__file__), 'module_test_sw'))

from etlup.tamalero import Baseline, Noisewidth
from qaqc.setup_config import SetupConfig
from qaqc.test_runner import TestRunner

def main():
    # Create the context
    context = SetupConfig(
        rb=1,
        rb_flavor=3,
        rb_serial_number="RB_001",
        modules={1: "MOD_A", 2: "MOD_B"},
        kcu_ipaddress="192.168.0.10",
        room_temp_celcius=25
    )

    # Initialize TestRunner
    runner = TestRunner(context)

    # Define the sequence of tests
    my_tests_sequence = [
        # "ReadoutBoardConnectionV0",
        Baseline.BaselineV0,
        Noisewidth.NoisewidthV0
    ]

    # Run the tests
    print("Starting test sequence...")
    runner.run_tests(my_tests_sequence)
    print("Test sequence completed.")

if __name__ == "__main__":
    main()
