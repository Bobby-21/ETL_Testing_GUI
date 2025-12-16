from module_test_sw.tamalero.ReadoutBoard import ReadoutBoard
from module_test_sw.tamalero.utils import get_kcu
from qaqc import register, required
from qaqc.errors import FailedTestCriteriaError
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

        # read/write to master lpgbt
        val = rb.DAQ_LPGBT.rd_reg("LPGBT.RWF.CHIPID.USERID0")
        wr_temp = 0 if val !=0 else 1
        rb.DAQ_LPGBT.wr_reg("LPGBT.RWF.CHIPID.USERID0", wr_temp)
        wr_temp_check = rb.DAQ_LPGBT.rd_reg("LPGBT.RWF.CHIPID.USERID0")
        if wr_temp != wr_temp_check:
            raise FailedTestCriteriaError(f"Master LPGBT communication failed. Attempted write of {wr_temp} but read back {wr_temp_check}")
        rb.DAQ_LPGBT.wr_reg("LPGBT.RWF.CHIPID.USERID0", val)

        # read/write from MUX64
        mux_val = rb.MUX64.read_adc(63, calibrate=False) # this selects channel and reads it read + write
        # assuming no error means success! checking if values make sense will be another test

        # read/write to servant lpgbt
        val = rb.TRIG_LPGBT.rd_reg("LPGBT.RWF.CHIPID.USERID0")
        wr_temp = 0 if val !=0 else 1
        rb.TRIG_LPGBT.wr_reg("LPGBT.RWF.CHIPID.USERID0", wr_temp)
        wr_temp_check = rb.TRIG_LPGBT.rd_reg("LPGBT.RWF.CHIPID.USERID0")
        if wr_temp != wr_temp_check:
            raise FailedTestCriteriaError(f"Servant LPGBT communication failed. Attempted write of {wr_temp} but read back {wr_temp_check}")
        rb.TRIG_LPGBT.wr_reg("LPGBT.RWF.CHIPID.USERID0", val)

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
