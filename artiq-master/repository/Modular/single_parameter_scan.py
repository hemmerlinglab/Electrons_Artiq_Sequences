from artiq.experiment import *
import numpy as np

import time
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_sequences import bare_counting, record_laser_frequencies
from build_functions import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import my_analyze
from base_functions import trapping_with_histogram, trapping_without_histogram
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

        my_analyze(self)
    
        return

    def run(self):

        # initiate scan

        if self.scan_ok:

            for my_ind in range(len(self.scan_values)):

                self.scheduler.pause()
                
                # Time cost tracker
                t0 = time.time()

                # set the new parameter
                scan_parameter(self, my_ind)
                record_laser_frequencies(self, my_ind)

                if self.mode == 'Trapping':

                    if self.histogram_on:
                        cts_trapped, cts_lost, cts_loading = trapping_with_histogram(self, my_ind)

                    else:
                        cts_trapped, cts_lost, cts_loading = trapping_without_histogram(self, my_ind)

                    # store result
                    self.mutate_dataset('trapped_signal', my_ind, cts_trapped)
                    self.mutate_dataset('lost_signal', my_ind, cts_lost)
                    self.mutate_dataset('loading_signal', my_ind, cts_loading)

                    # calculate ratios
                    self.mutate_dataset('ratio_signal', my_ind, cts_trapped / cts_loading)
                    self.mutate_dataset('ratio_lost', my_ind, cts_lost / cts_loading)

                    # reset timestamps
                    self.set_dataset('timestamps', [], broadcast=True)
                    self.set_dataset('timestamps_loading', [], broadcast=True)


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
                    self.mutate_dataset('scan_result', my_ind, cts)

                # time cost tracker
                self.mutate_dataset('time_cost', my_ind, time.time() - t0)

        return


