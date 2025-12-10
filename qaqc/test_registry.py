from qaqc.tests import baseline
from etlup.tamalero import Baseline, Noisewidth

TEST_REGISTRY = {
    Baseline.BaselineV0: baseline.run_baseline_test,
    Noisewidth.NoisewidthV0: None
}