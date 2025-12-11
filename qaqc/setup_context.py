from dataclasses import dataclass
from typing import Literal, Optional, Dict
try:
    from tamalero.ReadoutBoard import ReadoutBoard
except ImportError:
    from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard

@dataclass
class SetupContext:
    rb: int
    rb_flavor: Literal[3,6,7]
    rb_serial_number: str
    modules: Dict[int, str] # slot, module serial number -> will need to autogenerate a number based of serial number?

    readout_board: ReadoutBoard
    room_temp_celcius: Optional[int]
    
    @property
    def rb_config(self) -> Literal["modulev2", "rb7_modulev2", "rb6_modulev2"]:
        ...

    @property
    def module_ids(self) -> Dict[int, int]:
        ...

    @property
    def db_test_base(self) -> Dict:
        ...