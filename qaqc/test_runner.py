from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from module_test_sw.tamalero.KCU import KCU
from module_test_sw.tamalero.utils import get_kcu
from qaqc.setup_config import SetupConfig
from qaqc import TestSequence
from typing_extensions import List
from etlup import TestType
from qaqc.errors import FailedTestCriteriaError

class TestRunner:
    def __init__(self, setup_config: SetupConfig):
        self.setup_config: SetupConfig = setup_config

    def connect_kcu(self) -> KCU:
        """
        Returns the KCU object used for all communication with front end electronics
        """
        self.kcu = get_kcu(
            self.setup_config.kcu_ipaddress,
            control_hub=True,
            verbose=True
        )
        return self.kcu

    def connect_readout_board(self) -> ReadoutBoard:
        """
        Returns the Readout Board object that initializes communication with all the chips on the readout board
        """
        self.readout_board = ReadoutBoard(
            rb      = self.setup_config.rb, 
            trigger = True, 
            kcu     = self.connect_kcu(), 
            config  = self.setup_config.rb_config, 
            verbose = True
        )

    def run_tests(self, test_sequence: List[TestType]):
        """
        Executes each test in the sequence, in order, passing if any fail.
        """

        test_sequence = TestSequence(test_sequence)
        test_report = {}

        for test in test_sequence:
            try:
                test_results = test.run(
                    self.setup_config, 
                    test_report
                )
                test_report[test.model] = test_results
            except FailedTestCriteriaError as e:
                print(f"Failed Test: {e}")
                test_report[test.model] = None

        