# Main Tasks
1. Move Repo to BU repo
2. Making our first test: 
    - Figure out exactly what setup should be checked as the first test that ensures we have connection to the readout board before continuing
	- Instantiate `ReadoutBoard` object:
		- lpgbt (DAQ and Trigger) communication and configuration
		- MUX64 communication
		- VTRX+ communication
2. Making our second test:
    - Figure out range of reasonable values for MUX64 outputs
	- this may require checking we configure/name all the output values correctly!
3. Making our third test:
    - Figure out what tests need to be ran to exercise all wire bonds
	- translate this to tamalero functions!
4. Add Test Sequences to etlup and the database

## Sub Tasks
- In the event of a crash part way through the test, what do we do? -> best decided after using the GUI for a bit
	- Make sure previous results are outputted to a file to be able to feed back in later if a crash
		- tamalero has the concept of poke? to reconnect without needing to reinstatiate
- GUI interface for qaqc
- Unit Tests
	- Maybe a simulation mode that bypasses the actual functions to check everything but the business logic is correct
        - I would suggest a decorator on each of the test functions that uses the Pydantic model (ex: BaselineV0) and use the example attached to the model
