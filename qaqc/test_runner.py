# This will run the tests
from enum import Enum
from typing import Literal, Optional
from module_test_sw.tamalero import ReadoutBoard


class TestRoutineState:
    tests: list[object]

class SetupContext(Enum):
    rb: int
    rb_flavor: Literal[3,6,7]
    rb_serial_number: str
    modules: dict[int, str] # slot, module serial number -> will need to autogenerate a number based of serial number?

    readout_board: ReadoutBoard
    room_temp_celcius: Optional[int]

    # calculated fields
    # - rb config -> based off size unless supplied
    # - module number based off of str
    # - test_base so like time, module, readout board etc... to merge with the data for pydantic model

class TestRunner:
    ...


