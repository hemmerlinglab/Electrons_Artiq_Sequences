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

        return


