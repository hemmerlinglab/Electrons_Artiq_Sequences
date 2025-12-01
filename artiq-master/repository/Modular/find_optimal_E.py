from artiq.experiment import EnvExperiment
from artiq.coredevice.exceptions import RTIOOverflow, RTIOUnderflow
import time
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import optimizer_build
from prepare_functions import optimizer_prepare
from run_functions     import initial_sampling, bo_sampling, record_RTIO_error
from analyze_functions import optimizer_analyze

MAX_RETRIES = 3

class FindOptimalE(EnvExperiment):

    def build(self):

        optimizer_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        optimizer_prepare(self)

        return

    def analyze(self):

        optimizer_analyze(self)

        return

    def run(self):

        if not self.scan_ok:
            return

        initial_sampling(self)

        low_ei_count = 0
        for current_step in range(self.max_iteration):

            t0 = time.time()
            retries = 0

            while True:
                try: ei = bo_sampling(self, current_step)
                except (RTIOOverflow, RTIOUnderflow) as e:
                    record_RTIO_error(self, current_step, e)

                    # Not exceed maximum retries: retry the experiment for current set point
                    retries += 1
                    if retries <= MAX_RETRIES:
                        print(f"Retrying ({retries/MAX_RETRIES}) ...")
                        continue

                    # Exceed maximum retries: abort and save
                    print(f"Failed after {MAX_RETRIES} trials, terminating experiment ...")
                    return
                else: break

            # converge in advance: ei < tolerance event counter
            if ei < self.tolerance: low_ei_count += 1
            else: low_ei_count = 0

            self.mutate_dataset("time_cost", current_step + self.init_sample_size, time.time() - t0)

            # if the algorithm was already converged
            if (current_step + 1) >= self.min_iteration \
                    and low_ei_count >= self.converge_count:
                break

        return