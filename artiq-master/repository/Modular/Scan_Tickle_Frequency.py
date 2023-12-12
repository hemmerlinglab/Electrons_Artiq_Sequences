from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *
from base_sequences import *


class Scan_Tickle_Frequency_v2(EnvExperiment):
    
    def build(self):

        base_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        my_prepare(self)

    def analyze(self):

        my_analyse(self)
    
        return

    def run(self):


        self.tickler.set_level(self.tickle_level)
        
        self.tickler.on()
        
        for my_ind in range(len(self.scan_values)):

            print("Tickle frequency: {0:.3f} MHz".format(self.scan_values[my_ind]))

            self.scheduler.pause()

            
            # apply CW tickle pulse
            self.tickler.set_freq(self.scan_values[my_ind])

            self.count_events()

            extract = list(self.get_dataset('timestamps'))

            self.mutate_dataset('spectrum', my_ind, len(extract)) 
 
            # reset timestamps
            self.set_dataset('timestamps', [], broadcast=True)

        self.tickler.off()


