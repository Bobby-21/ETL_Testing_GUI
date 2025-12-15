import numpy as np
from ..setup_config import SetupConfig
from etlup.tamalero.Baseline import BaselineV0
from qaqc import register
from qaqc.errors import FailedTestCriteriaError
from typing_extensions import Dict
@register(BaselineV0)
def run_baseline_test(context: SetupConfig, previous_results: Dict) -> "BaselineV0":
    """
    Runs the baseline test.
    If 'config' is provided (from TestSequence), it uses it as a base/configuration.
    Returns a fully populated BaselineV0 instance.
    """
    raise FailedTestCriteriaError("shit something failed")
    data = {
        "module": "PBU0001", # Should come from context.modules
        "version": "v0",
        "name": "baseline",
        "measurement_date": "2023-01-01T12:00:00+01:00",
        "location": "BU",
        "user_created": "hayden",
        'ambient_celcius': 20,
        "etroc_0_Vtemp": 2713,
        "etroc_1_Vtemp": 2713,
        "etroc_2_Vtemp": 2713,
        "etroc_3_Vtemp": 2713,
        "bias_volts": 150,
        "pos_0": np.zeros((16, 16)).tolist(),
        "pos_1": np.zeros((16, 16)).tolist(),
        "pos_2": np.zeros((16, 16)).tolist(),
        "pos_3": np.zeros((16, 16)).tolist(),
    }
    
    return BaselineV0(**data)
