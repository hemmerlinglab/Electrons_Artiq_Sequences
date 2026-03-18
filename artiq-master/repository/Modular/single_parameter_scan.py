from artiq.experiment import EnvExperiment
from artiq.language.core import TerminationRequested
import sys
import os
import time

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import ofat_analyze
from run_functions     import measure, run_experiment_with_retries
from scan_functions    import scan_parameter

class SingleParamScan(EnvExperiment):

    def build(self):
        ofat_build(self)
        self.sequence_filename = os.path.abspath(__file__)

    def prepare(self):
        ofat_prepare(self)

    def analyze(self):
        ofat_analyze(self)

    def run(self):

        if not self.scan_ok:
            return

        validate_422 = True
        tolerance = 1e-4 if self.scanning_parameter == "frequency_422" else 1e-5

        for ind in range(len(self.scan_values)):

            try:

                # Record start time
                t0 = time.time()

                # Apply current setpoint
                scan_parameter(self, ind)

                # When scanning 422, compare against current scan value (variable target)
                expected_freq_422 = self.scan_values[ind] if self.scanning_parameter == "frequency_422" else None

                # Perform Experiment
                run_experiment_with_retries(
                    self, measure, ind,
                    validate_422=validate_422,
                    expected_freq_422=expected_freq_422,
                    tolerance=tolerance
                )

                # Record time cost for this experiment point
                self.mutate_dataset("time_cost", ind, time.time() - t0)

            except TerminationRequested:
                return