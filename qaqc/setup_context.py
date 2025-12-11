from enum import Enum
from typing import Literal, Optional
from module_test_sw.tamalero import ReadoutBoard

class SetupContext(Enum):
    rb: int
    rb_flavor: Literal[3,6,7]
    rb_serial_number: str
    modules: dict[int, str] # slot, module serial number -> will need to autogenerate a number based of serial number?

    readout_board: ReadoutBoard
    room_temp_celcius: Optional[int]
    
    @property
    def rb_config(self) -> Literal["modulev2", "rb7_modulev2", "rb6_modulev2"]:
        ...

    @property
    def module_ids(self) -> dict[int, int]:
        ...

    @property
    def db_test_base(self) -> dict:
        ...