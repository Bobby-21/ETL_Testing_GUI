import numpy as np
from ..test_runner import SetupContext, TestSequenceState
from etlup.tamalero.Baseline import BaselineV0

from typing import TYPE_CHECKING, Optional
import numpy as np
from ..test_runner import SetupContext

def run_baseline_test(context: SetupContext, state: "TestSequenceState", config: Optional["BaselineV0"] = None) -> "BaselineV0":
    """
    Runs the baseline test.
    If 'config' is provided (from TestSequence), it uses it as a base/configuration.
    Returns a fully populated BaselineV0 instance.
    """
    # Business logic to gather data
    # For example:
    # 1. Configure hardware based on context
    # 2. Run acquisition
    # 3. Process data
    
    # Placeholder data generation - Replace with actual logic
    # You can access context.readout_board, context.modules, etc.
    
    # If config is provided, we can use its values (e.g. bias_volts)
    bias_volts = config.bias_volts if config and config.bias_volts is not None else 150
    
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
        "bias_volts": bias_volts,
        "pos_0": np.zeros((16, 16)).tolist(),
        "pos_1": np.zeros((16, 16)).tolist(),
        "pos_2": np.zeros((16, 16)).tolist(),
        "pos_3": np.zeros((16, 16)).tolist(),
    }
    
    # Initialize the Pydantic model
    # Ensure BaselineV0 is imported in the file where this function is used
    # We return the data dict or construct the object if BaselineV0 was available at runtime
    # Since we are avoiding circular imports, we might need to return the dict or rely on the caller to construct
    # But typically the runner constructs it.
    
    # To construct it, we need to import it. But we can't import it at top level.
    # We can import it inside the function.
    return BaselineV0(**data)
