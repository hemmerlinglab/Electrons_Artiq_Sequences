from artiq.experiment import *
import numpy as np

import time
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_sequences import count_histogram, count_events, bare_counting, record_laser_frequencies
from base_functions import base_build, ofat_build, base_prepare, my_analyze
from scan_functions import scan_parameter

class SingleParamScan(EnvExperiment):

    def build(self):

        base_build(self)
        ofat_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        base_prepare(self)

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

                        # run detection sequence
                        count_histogram(self)

                        # get result
                        xs = self.get_dataset('hist_xs')
                        ys = self.get_dataset('hist_ys')
                        self.mutate_dataset('arr_of_timestamps', my_ind, self.get_dataset('timestamps'))

                        # calculate trapped count
                        ind_l = (xs > (self.load_time + self.wait_time - 1))[:-1]
                        ind_u = (xs < (self.load_time + self.wait_time + self.ext_pulse_length // 1000 + 3))[:-1]
                        cts_trapped = np.sum(ys[ind_l*ind_u])
                        #self.mutate_dataset('trapped_signal', my_ind, cts_trapped)

                        # calculate kicked out count
                        ind_l = (xs > (self.load_time + 4))[:-1]
                        if self.short_detection:
                            ind_u = (xs < min(self.load_time + 15, self.load_time + self.tickle_pulse_length + 3))[:-1]
                        else:
                            ind_u = (xs < (self.load_time + self.tickle_pulse_length + 3))[:-1]
                        print(ys[ind_l*ind_u])
                        cts_lost = np.sum(ys[ind_l*ind_u])
                        #self.mutate_dataset('lost_signal', my_ind, cts_lost)

                        # calculate loading count
                        ind_l = (xs > 1)[:-1]
                        ind_u = (xs < (self.load_time + 2))[:-1]
                        cts_loading = np.sum(ys[ind_l*ind_u])
                        #self.mutate_dataset('loading_signal', my_ind, cts_loading)                     

                    else:

                        # run detection sequence
                        count_events(self)

                        # get result
                        events = np.array(self.get_dataset('timestamps'))
                        cts_loading = len(events[events<(self.load_time + 2)])
                        cts_trapped = len(events[events>(self.load_time + self.wait_time -3)])
                        cts_lost = 0

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


