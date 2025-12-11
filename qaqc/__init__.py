# In ETLUP you should have a variable called TestSequences
# this should store all the TestSequencs
# so then you can loop through and convert them into test sequences

# This will run the tests
from etlup import TestType
from qaqc.test_registry import TEST_REGISTRY
from typing_extensions import List

class TestWrapper:
    def __init__(self, test_model: TestType, func):
        self.model = test_model
        self.func = func

    def run(self, *args, **kwargs):
        if self.func is None:
            raise NotImplementedError(f"Test function for {self.model} is not implemented.")
        return self.func(*args, **kwargs)

class TestSequence:
    """
    A user friendly common interface between the test sequences defined in etlup and the test functions defined in qaqc/tests. 
    Mapping between the etlup test models and the functions is done in the test_registry.py module.
 
    Usage:
        seq = TestSequence([BaselineV0, NoisewidthV0])
        for test in seq:
            test.run()
            
        # Or access by index
        seq[0].run()
    """

    def __init__(self, sequence: List[TestType]):
        self.sequence: list = sequence

    def __iter__(self):
        for test in self.sequence:
            yield TestWrapper(test, TEST_REGISTRY.get(test))

    def __getitem__(self, index):
        test = self.sequence[index]
        return TestWrapper(test, TEST_REGISTRY.get(test))