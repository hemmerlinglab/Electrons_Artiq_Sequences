from artiq.experiment import EnvExperiment
import sys
import os
import time

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import doe_build
from prepare_functions import doe_prepare
from analyze_functions import doe_analyze
from run_functions     import measure, run_experiment_with_retries
from scan_functions    import set_doe_parameters

class DOEScan(EnvExperiment):

    def build(self):
        doe_build(self)
        self.sequence_filename = os.path.abspath(__file__)

    def prepare(self):
        doe_prepare(self)

    def analyze(self):
        doe_analyze(self)

    def run(self):

        if not self.scan_ok:
            return

        if self.utility_mode == "DOE Scan":

            for ind, row in self.setpoints.iterrows():

                # Record start time
                t0 = time.time()

                # Apply current setpoint
                set_doe_parameters(self, row, ind, self.steps)

                # Perform Experiment
                run_experiment_with_retries(self, measure, ind)

                # Record time cost for this experiment point
                self.mutate_dataset("time_cost", ind, time.time() - t0)

        elif self.utility_mode == "Single Experiment":
            run_experiment_with_retries(self, measure, 0)
