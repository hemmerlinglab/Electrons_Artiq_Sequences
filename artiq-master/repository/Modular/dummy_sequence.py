from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")

from helper_functions import *
from base_sequences import *
from base_functions import *
from scan_functions import scan_parameter

class Dummy_Sequence(EnvExperiment):
    
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

                #if self.show_histogram:

                #    count_histogram(self)
                #    
                #    # update data
                #    xs = self.get_dataset('hist_xs')
                #    ys = self.get_dataset('hist_ys')

                #    ind_l = (xs > (self.load_time + self.wait_time - 1 / self.bin_width))[:-1]
                #    ind_u = (xs < (self.load_time + self.wait_time + 3 / self.bin_width))[:-1]
                #    cts_trapped = np.sum(ys[ind_l*ind_u])
                #    self.mutate_dataset('trapped_signal', my_ind, cts_trapped)                     
                #    self.mutate_dataset('arr_of_timestamps', my_ind, self.get_dataset('timestamps')) 

                #    ind_l = (xs > (1 / self.bin_width))[:-1]
                #    ind_u = (xs < (self.load_time / self.bin_width))[:-1]
                #    cts_loading = np.sum(ys[ind_l*ind_u])
                #    self.mutate_dataset('loading_signal', my_ind, cts_loading)                     
                #    self.mutate_dataset('arr_of_timestamps_loading', my_ind, self.get_dataset('timestamps_loading')) 

                #    self.mutate_dataset('ratio_signal', my_ind, cts_trapped / cts_loading)

                #else:

                #    count_events(self)

                #    extract = np.array(self.get_dataset('timestamps'))
                #    trapped = extract[extract > (self.load_time+5)]
                #    loading = extract[extract < (self.load_time+5)]
                #    cts_trapped = len(trapped)
                #    cts_loading = len(loading)

                #    self.mutate_dataset('trapped_signal', my_ind, cts_trapped)
                #    self.mutate_dataset('loading_signal', my_ind, cts_loading)
                #    self.set_dataset('timestamps', trapped, broadcast=True)
                #    self.set_dataset('timestamps_loading', loading, broadcast=True)

                #    try:
                #        self.mutate_dataset('ratio_signal', my_ind, cts_trapped / cts_loading)
                #    except:
                #        pass
 
                ## reset timestamps
                #self.set_dataset('timestamps', [], broadcast=True)
                #self.set_dataset('timestamps_loading', [], broadcast=True)

        return


