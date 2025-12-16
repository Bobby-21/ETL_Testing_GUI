# QAQC 

### Developing etlup Locally for QAQC
If you need to locally develop etlup instead of using a prebuilt python package. You can install as editable,
```
uv remove etlup
uv pip install -U -e /path/to/etlup/
```
And to reinstall,
```
uv remove etlup
uv add etlup
```

# Examples

## Running a Sequence of Tests
Here is an example of running a sequence (well just one in this case) on a module.
```python
# imports
session = Session(
    rb=0,
    rb_size=3,
    rb_serial_number="RB_001",
    modules=["MOD_A", None, None],
    kcu_ipaddress="192.168.0.10",
    room_temp_celcius=25
)
my_tests_sequence = [
    ReadoutBoardCommunication.ReadoutBoardCommunicationV0,
]
print("Starting test sequence...")
for test, result in session.iter_test_sequence(my_tests_sequence, slot=0):
    if isinstance(result, Exception):
        print(f"Test {test.model} failed: {result}")
    else:
        print(f"Test {test.model} passed")
```
Highlights
- `session` object intialized with all the setup/external information
- test sequences are lists of pydantic models
    - `etlup` will also have predefined test sequences to be compatable with the database
- `session.iter_test_sequence(my_tests_sequence, slot=0)` allows you to loop throgh and executes each test in the sequence on a particular slot of the readout board
    - it stores the results in the session
        - `session.results` is a tuple of dictionaries, one for each slot on the readout baord. Each dictionary holds all the tests results on a particular module in that slot. Keys are the pydantic model and the value is the data (instantiated pydantic model) in the dictionary unless it fails then the value is None.
    - tells you if a test has failed

## Making a new Test
Here is an example, it is by no means following a QAQC procedure.

**Note, tests should apply to entire modules only!**
```python
@register(NoisewidthV0)
@required(["ReadoutBoardCommunicationV0", Baseline.BaselineV0])
def test(session) -> NoisewidthV0:
    """
    Runs the baseline test.
    If 'config' is provided (from TestSequence), it uses it as a base/configuration.
    Returns a fully populated BaselineV0 instance.
    """    
    data = session.current_base_data | {
        'ambient_celcius': 20,
        "etroc_0_Vtemp": 2713,
        "etroc_1_Vtemp": 2713,
        "etroc_2_Vtemp": 2713,
        "etroc_3_Vtemp": 2713,
        "bias_volts": 150,
        "pos_0": np.zeros((16, 16)).tolist(),
        "pos_1": np.zeros((16, 16)).tolist(),
        "pos_2": np.zeros((16, 16)).tolist(),
        "pos_3": np.zeros((16, 16)).tolist()
    }
    
    return NoisewidthV0(**data)
```

Highlights:
- `@register` decorator registers it as a QAQC test that can be performed. It associates the function `test` with the pydantic model ([click here for information on pydantic models](https://docs.pydantic.dev/latest/concepts/models/)) `NoisewidthV0` [click here for more the NoisewidthV0 pydantic model](https://gitlab.cern.ch/cms-etl-electronics/etlup/-/blob/ff687f9257f55a884d81596f55410c2d50a6a42c/src/etlup/tamalero/Noisewidth.py). 
- `@requires` allows you to require that those tests need to have been ran prior to running the below function
- `session` this is passed into every test function and is the only argument. (see `session.py`) It carries:
    - prior results
    - environment setup
    - tamalero readout board and kcu objects
    - It also provides you with the `current_base_data` to make the pydantic models (module being tested, location, version, name of the test etc...)

- If a test failes a basic criteria please raise this exection `qaqc.errors.FailedTestCriteriaError`
