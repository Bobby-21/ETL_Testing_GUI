from typing import Optional, Dict, Any, Literal
from module_test_sw.tamalero.KCU import KCU
from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard

class Session:
    def __init__(
        self,
        kcu_ipaddress: str,
        rb: int,
        rb_flavor: Literal[3,6,7],
        rb_serial_number: str,
        modules: Dict[int, str],
        room_temp_celcius: Optional[int] = None
    ):
        # Config variables
        self.kcu_ipaddress = kcu_ipaddress
        self.rb = rb
        self.rb_flavor = rb_flavor
        self.rb_serial_number = rb_serial_number
        self.modules = modules
        self.room_temp_celcius = room_temp_celcius

        # Session state
        self.kcu: Optional[KCU] = None
        self.readout_board: Optional[ReadoutBoard] = None
        self.results: Dict[Any, Any] = {}

    @property
    def rb_config(self) -> Literal["modulev2", "rb7_modulev2", "rb6_modulev2"]:
        """
        Depending on the flavor choose one of these configs.
        This config is used to instantiate a readout board.
        """
        if self.rb_flavor == 7:
            return "rb7_modulev2"
        elif self.rb_flavor == 6:
            return "rb6_modulev2"
        else:
            return "modulev2"

    @property
    def module_ids(self) -> Dict[int, int]:
        """
        Tamalero requires a numerical number when instantiating.
        Will probably just take the numerical part of the serial number.
        """
        ...

    def db_test_base(self, slot: int) -> Dict:
        """
        A dictionary of all the information in SetupConfig for the upload of a test of a module
        """

    def clear(self):
        self.kcu = None
        self.readout_board = None
        self.results = {}
