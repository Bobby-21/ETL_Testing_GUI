from qaqc.setup_config import SetupConfig
from qaqc import TestSequence
from typing_extensions import List
from etlup import TestType
from qaqc.errors import FailedTestCriteriaError
from qaqc.session import global_session as session

class TestRunner:
    def __init__(self, setup_config: SetupConfig):
        self.setup_config: SetupConfig = setup_config
        session.clear()
        session.setup_config = setup_config

    def run_tests(self, test_sequence: List[TestType]):
        """
        Executes each test in the sequence, in order, passing if any fail.
        """

        test_sequence = TestSequence(test_sequence)

        for test in test_sequence:
            try:
                test_results = test.run(session)
                session.test_results[test.model] = test_results
            except FailedTestCriteriaError as e:
                print(f"Failed Test: {e}")
                session.test_results[test.model] = None

        