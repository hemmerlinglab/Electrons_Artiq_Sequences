from artiq.experiment import *
import numpy as np

import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_sequences import count_histogram
from base_functions import base_build, my_prepare, my_analyze
from scan_functions import scan_parameter

class General_Scan(EnvExperiment):
    
    def build(self):

        base_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        my_prepare(self)

    def analyze(self):

        my_analyze(self)
    
        return

    def run(self):

        # initiate scan

        if self.scan_ok:

            for my_ind in range(len(self.scan_values)):

                self.scheduler.pause()

                # set the new parameter
                scan_parameter(self, my_ind)

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

        return


