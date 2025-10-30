from artiq.experiment import *
import time
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_sequences import bare_counting, record_laser_frequencies
from build_functions import doe_build
from prepare_functions import doe_prepare
from analyze_functions import doe_analyze
from run_functions import trapping_with_histogram, trapping_without_histogram, store_to_dataset
from scan_functions import set_doe_parameters

class DOEScan(EnvExperiment):

    def build(self):
        
        doe_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        doe_prepare(self)

        return

    def analyze(self):

        doe_analyze(self)

        return

    def run(self):

        if self.scan_ok:

            for ind, row in self.setpoints.iterrows():

                self.scheduler.pause()
                t0 = time.time()

                set_doe_parameters(self, row, ind, self.steps)
                record_laser_frequencies(self, ind)

                if self.mode == "Trapping":
                    if self.histogram_on:
                        cts_trapped, cts_lost, cts_loading = trapping_with_histogram(self, ind)

                    else:
                        cts_trapped, cts_lost, cts_loading = trapping_without_histogram(self, ind)

                    store_to_dataset(self, ind, cts_trapped, cts_lost, cts_loading)

                elif self.mode == 'Counting':
                    """
                    Counting mode information sheet:
                    laser: Controlled
                    tickle: As long as `tickle_on` was set to off, it would be fine
                    RF Drive: Kept off
                    DC multipoles: Controlled, so set to 0 if not wanted
                    extraction pulse: Not triggered
                    mesh: Controlled
                    MCP front: Controlled
                    
                    Tips:
                    1. I know RF could increase electron count, but I would prefer not
                       to introduce extra attributes now, so turn it on from code if you
                       really need it, or just add this attribute if you want.
                    """

                    cts = bare_counting(self)
                    self.mutate_dataset('scan_result', ind, cts)

                # time cost tracker
                self.mutate_dataset('time_cost', ind, time.time() - t0)