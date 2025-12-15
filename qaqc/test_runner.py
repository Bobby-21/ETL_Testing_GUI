from qaqc import TestSequence
from typing_extensions import List
from etlup import TestType
from qaqc.errors import FailedTestCriteriaError
from qaqc.session import Session

class TestRunner:
    def __init__(self, session: Session):
        self.session = session
        self.session.clear()

    def run_test_sequence(self, test_sequence: List[TestType], slot: int) -> None:
        """
        On a particular slot of the Readout Board, execute the inputted test_sequence.

        Test Results will be stored in the session
        """
        if not slot in self.session.active_slots:
            raise ValueError(f"This slot was configured to not be tested. Configured modules: {self.session.modules}")

        session_results = self.session.results[slot]
        test_sequence = TestSequence(test_sequence)

        for test in test_sequence:
            try:
                results = test.run(self.session)
                session_results[test.model] = results
            except FailedTestCriteriaError as e:
                print(f"Failed Test: {e}")
                session_results[test.model] = None
            