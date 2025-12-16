from __future__ import annotations
from typing import Optional, Dict, Any, Literal, List
from module_test_sw.tamalero.KCU import KCU
from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from qaqc import TestSequence
from typing_extensions import List, Dict
from etlup import TestType, now_utc
from etlup.base_model import ConstructionBase
from qaqc.errors import FailedTestCriteriaError, MissingRequiredTestError

class RbSizeTuple(tuple):
    """
    Just renaming for clarity, that these tuples have size length of rb_size
    """
    def __new__(cls, iterable, size: int):
        instance = super().__new__(cls, iterable)
        if len(instance) != size:
            raise ValueError(f"Expected tuple of size {size}, but got {len(instance)}")
        return instance

    def __class_getitem__(cls, item):
        return cls

class Session:
    def __init__(
        self,
        kcu_ipaddress: str,
        rb: int,
        rb_size: Literal[3,6,7],
        rb_serial_number: str,
        modules: List[str],
        location: str = "Fermilab",
        user_created: str = "unknown",
        room_temp_celcius: Optional[int] = None
    ):
        # Config variables
        self.kcu_ipaddress: str = kcu_ipaddress
        self.rb: int = rb
        self.rb_size: int = rb_size
        self.rb_serial_number = rb_serial_number
        self.modules: RbSizeTuple = RbSizeTuple(modules, size=rb_size)
        self.location = location
        self.user_created = user_created
        self.room_temp_celcius: float = room_temp_celcius

        # Session state
        self.kcu: Optional[KCU] = None
        self.readout_board: Optional[ReadoutBoard] = None
        self.results: RbSizeTuple[Dict[Any,Any]] = RbSizeTuple(
            [{} for _ in range(self.rb_size)], 
            size=self.rb_size)

        self.current_base_data: dict = None # current base data for pydantic etlup modules

    @property
    def active_slots(self) -> List[int]:
        return [i for i in range(len(self.modules)) if self.modules[i] is not None]

    @property
    def rb_config(self) -> Literal["modulev2", "rb7_modulev2", "rb6_modulev2"]:
        """
        Depending on the flavor choose one of these configs.
        This config is used to instantiate a readout board.
        """
        if self.rb_size == 7:
            return "rb7_modulev2"
        elif self.rb_size == 6:
            return "rb6_modulev2"
        else:
            return "modulev2"

    @property
    def module_ids(self) -> RbSizeTuple[int]:
        """
        Tamalero requires a numerical number when instantiating.
        Will probably just take the numerical part of the serial number.
        """
        # TODO: make this actually use the module numbers?
        return [i+100 for i in range(self.rb_size)]

    def iter_test_sequence(self, test_sequence: List[TestType], slot: int):
        """
        On a particular slot of the Readout Board, execute the inputted test_sequence.

        Test Results will be stored in the session
        """
        if not slot in self.active_slots:
            raise ValueError(f"This slot was configured to not be tested. Configured modules: {self.session.modules}")
        self.current_base_data = None # drop any current base data
        
        session_results = self.results[slot]
        test_sequence = TestSequence(test_sequence)

        for test in test_sequence:
            self.current_base_data = self.get_base_data(
                test.model, slot)
            try:
                results = test.run(self)
                if not isinstance(results, test.model):
                    raise ValueError(f"Tests returned need to be of pydantic model: {test.model} but got {type(results)}")
                session_results[test.model] = results
                yield test, results
            except (FailedTestCriteriaError, MissingRequiredTestError) as e:
                session_results[test.model] = None
                yield test, e

        self.current_base_data = None

    def get_base_data(self, test_model: TestType, slot: int) -> Dict:
        """
        A dictionary of all the information in SetupConfig for the upload of a test of a module
        """
        res = {}
        for field in ConstructionBase.model_fields:
            if field == "measurement_date":
                res[field] = now_utc()
            elif field == "location":
                res[field] = self.location
            elif field == "user_created":
                res[field] = self.user_created
            elif field == "module":
                res[field] = self.modules[slot]
        
        if "version" in test_model.model_fields:
            res["version"] = test_model.model_fields["version"].default
        if "name" in test_model.model_fields:
            res["name"] = test_model.model_fields["name"].default

        return res

    def clear(self):
        self.kcu = None
        self.readout_board = None
        self.results = RbSizeTuple(
            [{} for _ in range(self.rb_size)], 
            size=self.rb_size)
        self.current_base_data = None