from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from module_test_sw.tamalero.utils import get_kcu
from qaqc import register, required
from qaqc.session import global_session as session

@register("ReadoutBoardConnectionV0")
@required([])
def readout_board_connection_test(session_obj):
    """
    Connects to the KCU and Readout Board.
    Populates session.kcu and session.readout_board.
    """
    print("Connecting to KCU...")
    session.kcu = get_kcu(
        session.setup_config.kcu_ipaddress,
        control_hub=True,
        verbose=True
    )

    print("Connecting to Readout Board...")
    session.readout_board = ReadoutBoard(
        rb      = session.setup_config.rb, 
        trigger = True, 
        kcu     = session.kcu, 
        config  = session.setup_config.rb_config, 
        verbose = True
    )
    
    return "Connected"
