from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from module_test_sw.tamalero.utils import get_kcu
from qaqc import register, required

@register("ReadoutBoardConnectionV0")
@required([])
def readout_board_connection_test(session):
    """
    Connects to the KCU and Readout Board.
    Populates session.kcu and session.readout_board.
    """
    print("Connecting to KCU...")
    session.kcu = get_kcu(
        session.kcu_ipaddress,
        control_hub=True,
        verbose=True
    )

    print("Connecting to Readout Board...")
    session.readout_board = ReadoutBoard(
        rb      = session.rb, 
        trigger = True, 
        kcu     = session.kcu, 
        config  = session.rb_config, 
        verbose = True
    )
    
    return "Connected"
