from artiq.experiment import EnvExperiment
from artiq.language.core import TerminationRequested
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

                try:

                    # Record start time
                    t0 = time.time()

                    # Apply current setpoint
                    set_doe_parameters(
                        self, row, ind, self.steps,
                        param_names=getattr(self, "doe_param_names", None)
                    )

                    # Perform Experiment
                    run_experiment_with_retries(self, measure, ind)

                    # Record time cost for this experiment point
                    self.mutate_dataset("time_cost", ind, time.time() - t0)

                except TerminationRequested:
                    return
                except Exception as e:
                    print(f"Experiment terminated early at point {ind}: {e}")
                    return

        elif self.utility_mode == "Single Experiment":
            try:
                run_experiment_with_retries(self, measure, 0)
            except TerminationRequested:
                return
            except Exception as e:
                print(f"Single experiment terminated early: {e}")
                return
