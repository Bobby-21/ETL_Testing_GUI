from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from module_test_sw.tamalero.KCU import KCU
from module_test_sw.tamalero.utils import get_kcu
from setup_config import SetupConfig

class TestRunner:
    def __init__(self, setup_config: SetupConfig):
        self.setup_config: SetupConfig = setup_config

    def connect_kcu(self) -> KCU:
        """
        Returns the KCU object used for all communication with front end electronics
        """
        self.kcu = get_kcu(
            self.setup_config.kcu_ipaddress,
            control_hub=True,
            verbose=True
        )
        return self.kcu

    def connect_readout_board(self) -> ReadoutBoard:
        """
        Returns the Readout Board object that initializes communication with all the chips on the readout board
        """
        self.readout_board = ReadoutBoard(
            rb      = self.setup_config.rb, 
            trigger = True, 
            kcu     = self.connect_kcu(), 
            config  = self.setup_config.rb_config, 
            verbose = True
        )

    def run_tests(self, test_sequence):
        ...