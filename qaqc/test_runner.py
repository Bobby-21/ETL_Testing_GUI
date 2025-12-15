from qaqc import TestSequence
from typing_extensions import List, Dict
from etlup import TestType, now_utc
from etlup.base_model import ConstructionBase
from qaqc.errors import FailedTestCriteriaError, MissingRequiredTestError
from qaqc.session import Session

class TestRunner:
    def __init__(self, session: Session):
        self.session = session
        self.session.clear()
        
    def iter_test_sequence(self, test_sequence: List[TestType], slot: int):
        """
        On a particular slot of the Readout Board, execute the inputted test_sequence.

        Test Results will be stored in the session
        """
        if not slot in self.session.active_slots:
            raise ValueError(f"This slot was configured to not be tested. Configured modules: {self.session.modules}")
        self.session.current_base_data = None # drop any current base data
        
        session_results = self.session.results[slot]
        test_sequence = TestSequence(test_sequence)

        for test in test_sequence:
            self.session.current_base_data = self.get_base_data(
                test.model, slot)
            try:
                results = test.run(self.session)
                if not isinstance(results, test.model):
                    raise ValueError(f"Tests returned need to be of pydantic model: {test.model} but got {type(results)}")
                session_results[test.model] = results
                yield test, results
            except (FailedTestCriteriaError, MissingRequiredTestError) as e:
                session_results[test.model] = None
                yield test, e

        self.session.current_base_data = None

    def get_base_data(self, test_model: TestType, slot: int) -> Dict:
        """
        A dictionary of all the information in SetupConfig for the upload of a test of a module
        """
        res = {}
        for field in ConstructionBase.model_fields:
            if field == "measurement_date":
                res[field] = now_utc()
            elif field == "location":
                res[field] = self.session.location
            elif field == "user_created":
                res[field] = self.session.user_created
            elif field == "module":
                res[field] = self.session.modules[slot]
        
        if "version" in test_model.model_fields:
            res["version"] = test_model.model_fields["version"].default
        if "name" in test_model.model_fields:
            res["name"] = test_model.model_fields["name"].default

        return res