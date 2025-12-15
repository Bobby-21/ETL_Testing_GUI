import numpy as np
from ..setup_config import SetupConfig
from etlup.tamalero.Noisewidth import NoisewidthV0
from qaqc import register

@register(NoisewidthV0)
def run_noisewidth_test(context: SetupConfig, previous_results: list) -> NoisewidthV0:
    """
    Runs the baseline test.
    If 'config' is provided (from TestSequence), it uses it as a base/configuration.
    Returns a fully populated BaselineV0 instance.
    """
    
    data = {
        "module": "PBU0001",
        "version": "v0",
        "name": "noisewidth",
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
    
    return NoisewidthV0(**data)
