from qaqc import register, required
from qaqc.errors import FailedTestCriteriaError
from etlup.tamalero.MUX64Values import MUX64ValuesV0
import yaml
from pathlib import Path

@register(MUX64ValuesV0)
@required(["ReadoutBoardCommunicationV0"])
def test(session):
    """
    Reads all 64 MUX64 channels and verifies values are within expected range.
    """
    try:
        rb = session.readout_board

        # load allowable MUX64 values from yaml
        mux_yaml_path = Path(__file__).parent / 'configs' / 'mux64_values.yaml'
        with open(mux_yaml_path, 'r') as f:
            allowable_mux64_values = yaml.safe_load(f)

        # read all 64 MUX64 channels
        mux_values = []
        mux_checks = []
        bad_pin_val_pairs = []
        for i in range(64):
            val = rb.MUX64.read_adc(i, calibrate=False)
            mux_values.append(val)

            # verify values are within expected range
            val_min = allowable_mux64_values[i]['min']
            val_max = allowable_mux64_values[i]['max']
            if val < val_min or val > val_max:
                mux_checks.append(False)
                bad_pin_val_pairs.append((i, val))
            else:
                mux_checks.append(True)

        all_values_passed = all(mux_checks)
        if not all_values_passed:
            raise FailedTestCriteriaError(f"MUX64 out-of-range readings (pin, val): {bad_pin_val_pairs}")

    except Exception as e:
        raise FailedTestCriteriaError(str(e))
        
    data = {
        "mux64_all_passed": all_values_passed,
        "mux64_values": mux_values,
        "mux64_checks": mux_checks,
        "mux64_bad_pin_val_pairs": bad_pin_val_pairs
    }

    return MUX64ValuesV0(**data)
