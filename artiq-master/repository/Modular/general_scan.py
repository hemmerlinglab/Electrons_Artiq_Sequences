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

                if self.show_histogram:
                    
                    count_histogram(self)
                    
                    # update data
                    xs = self.get_dataset('hist_xs')
                    ys = self.get_dataset('hist_ys')
                    
                    ind_l = (xs > (self.extraction_time - 1 / self.bin_width))[:-1]
                    ind_u = (xs < (self.extraction_time + 3 / self.bin_width))[:-1]
                    cts = np.sum(ys[ind_l*ind_u])
                    self.mutate_dataset('trapped_signal', my_ind, cts)                     
                    self.mutate_dataset('arr_of_timestamps', my_ind, self.get_dataset('timestamps')) 

                    ind_l = (xs > (1 / self.bin_width))[:-1]
                    ind_u = (xs < (20 / self.bin_width))[:-1]
                    cts = np.sum(ys[ind_l*ind_u])
                    self.mutate_dataset('loading_signal', my_ind, cts)                     
                    self.mutate_dataset('arr_of_timestamps_loading', my_ind, self.get_dataset('timestamps_loading')) 

                else:
                    count_events(self)

                    extract = list(self.get_dataset('timestamps'))
                    self.mutate_dataset('trapped_signal', my_ind, len(extract))

                    extract = list(self.get_dataset('timestamps_loading'))
                    self.mutate_dataset('loading_signal', my_ind, len(extract)) 
 
                # reset timestamps
                self.set_dataset('timestamps', [], broadcast=True)
                self.set_dataset('timestamps_loading', [], broadcast=True)

        return


