from __future__ import annotations
from typing import Optional, Dict, Any, Literal, List
from module_test_sw.tamalero.KCU import KCU
from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard

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

    def clear(self):
        self.kcu = None
        self.readout_board = None
        self.results = RbSizeTuple(
            [{} for _ in range(self.rb_size)], 
            size=self.rb_size)
        self.current_base_data = None
