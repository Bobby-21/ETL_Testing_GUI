from typing import Optional, Dict, Any
from module_test_sw.tamalero.KCU import KCU
from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from qaqc.setup_config import SetupConfig

class Session:
    def __init__(self):
        self.kcu: Optional[KCU] = None
        self.readout_board: Optional[ReadoutBoard] = None
        self.setup_config: Optional[SetupConfig] = None
        self.test_results: Dict[Any, Any] = {}

    def clear(self):
        self.kcu = None
        self.readout_board = None
        self.setup_config = None
        self.test_results = {}

# Global instance
global_session = Session()

