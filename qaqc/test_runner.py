from qaqc import TestSequence
from typing_extensions import List
from etlup import TestType
from qaqc.errors import FailedTestCriteriaError
from qaqc.session import Session

class TestRunner:
    def __init__(self, session: Session):
        self.session = session
        self.session.clear()

    def run_tests(self, test_sequence: List[TestType]):
        """
        Executes each test in the sequence, in order, passing if any fail.
        """

        test_sequence = TestSequence(test_sequence)

        for test in test_sequence:
            try:
                results = test.run(self.session)
                self.session.results[test.model] = results
            except FailedTestCriteriaError as e:
                print(f"Failed Test: {e}")
                self.session.results[test.model] = None