# In ETLUP you should have a variable called TestSequences
# this should store all the TestSequencs
# so then you can loop through and convert them into test sequences

# This will run the tests
from etlup import TestType
from typing_extensions import List
import functools
from qaqc.errors import MissingRequiredTestError
# from qaqc.session import session

TEST_REGISTRY = {}

def register(test_type):
    """
    Decorator to register a function as a handler for a specific TestType.
    """
    def decorator(func):
        TEST_REGISTRY[test_type] = func
        return func
    return decorator

def required(required_tests: List[TestType]):
    """
    Decorator to ensure that specific tests have passed before running the decorated test.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session, *args, **kwargs):
            for req in required_tests:
                if req not in session.results:
                    raise MissingRequiredTestError(f"Required test {req} was not run for {func.__name__}.")
            return func(session, *args, **kwargs)
        return wrapper
    return decorator

class TestWrapper:
    def __init__(self, test_model: TestType, func):
        self.model = test_model
        self.func = func

    def run(self, session):
        if self.func is None:
            raise NotImplementedError(f"Test function for {self.model} is not implemented.")
        return self.func(session)


class TestSequence:
    """
    A user friendly common interface between the test sequences defined in etlup and the test functions defined in qaqc/tests. 
    Mapping between the etlup test models and the functions is done via the @register decorator in qaqc/__init__.py.
 
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

import qaqc.tests # Ensure tests are registered