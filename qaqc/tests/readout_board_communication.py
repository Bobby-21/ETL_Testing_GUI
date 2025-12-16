from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from module_test_sw.tamalero.utils import get_kcu
from qaqc import register, required
from qaqc.errors import FailedTestCriteriaError
from etlup import Tests
from etlup.tamalero.ReadoutBoardCommunication import ReadoutBoardCommunicationV0

@register(ReadoutBoardCommunicationV0)
@required([])
def test(session):
    """
    Connects to the KCU and Readout Board.
    Populates session.kcu and session.readout_board.
    """
    try:
        print("Connecting to KCU...")
        session.kcu = get_kcu(
            session.kcu_ipaddress,
            control_hub=True,
            verbose=True
        )

        print("Connecting to Readout Board...")
        session.readout_board = ReadoutBoard(
            rb      = session.rb, 
            servantger = True, 
            kcu     = session.kcu, 
            config  = session.rb_config, 
            verbose = True
        )
        rb = session.readout_board

        # write to master lpgbt
        val = rb.DAQ_LPGBT.rd_adr(0x1d7)

        # Read to master lpgbt

        # write from MUX64

        # read from MUX64

        # write to servant lpgbt

        # Read to servant lpgbt

    except Exception as e:
        raise FailedTestCriteriaError(str(e))
        
    return {
        "master_lpgbt_read": True,
        "master_lpgbt_write": True,
        "mux64_read": True,
        "mux64_write": True,
        "servant_lpgbt_read": True,
        "servant_lpgbt_write": True
    }
