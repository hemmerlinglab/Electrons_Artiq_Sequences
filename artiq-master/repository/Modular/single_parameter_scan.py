from artiq.experiment import *
import numpy as np

import time
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_sequences import bare_counting, record_laser_frequencies
from build_functions import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import ofat_analyze
from run_functions import trapping_with_histogram, trapping_without_histogram, store_to_dataset
from scan_functions import scan_parameter

class SingleParamScan(EnvExperiment):

    def build(self):

        ofat_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        ofat_prepare(self)

        return

    def analyze(self):

        ofat_analyze(self)
    
        return

    def run(self):

        # initiate scan

        if not self.scan_ok:
            return

        for ind in range(len(self.scan_values)):

            self.scheduler.pause()
            
            # Time cost tracker
            t0 = time.time()

            # set the new parameter
            scan_parameter(self, ind)
            record_laser_frequencies(self, ind)

            if self.mode == 'Trapping':

                if self.histogram_on:
                    cts_trapped, cts_lost, cts_loading = trapping_with_histogram(self, ind)

                else:
                    cts_trapped, cts_lost, cts_loading = trapping_without_histogram(self, ind)

                # store result
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

        return
