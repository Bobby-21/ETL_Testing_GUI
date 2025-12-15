
class FailedTestCriteriaError(Exception):
    """
    Use this error when a test does not pass the basic criteria
    """

class MissingRequiredTestError(Exception):
    """
    Internal error for when a test was missing a previous required test.
    """