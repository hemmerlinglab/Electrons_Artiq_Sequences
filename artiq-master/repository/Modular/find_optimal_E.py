from artiq.experiment import EnvExperiment
import time
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import optimizer_build
from prepare_functions import optimizer_prepare
from run_functions     import initial_sampling, bo_sampling, run_experiment_with_retries
from analyze_functions import optimizer_analyze

class FindOptimalE(EnvExperiment):

    def build(self):
        optimizer_build(self)
        self.sequence_filename = os.path.abspath(__file__)

    def prepare(self):
        optimizer_prepare(self)

    def analyze(self):
        optimizer_analyze(self)

    def run(self):

        if not self.scan_ok:
            return

        initial_sampling(self)

        low_ei_count = 0
        for current_step in range(self.max_iteration):

            t0 = time.time()

            ei = run_experiment_with_retries(self, bo_sampling, current_step)

            # converge in advance: ei < tolerance event counter
            if ei < self.tolerance: low_ei_count += 1
            else: low_ei_count = 0

            self.mutate_dataset("time_cost", current_step + self.init_sample_size, time.time() - t0)

            # if the algorithm was already converged
            if (current_step + 1) >= self.min_iteration \
                    and low_ei_count >= self.converge_count:
                break
