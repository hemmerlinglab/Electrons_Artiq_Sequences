from artiq.experiment import EnvExperiment
import numpy as np
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import ofat_analyze
from scan_functions    import scan_parameter

class Dummy_Sequence(EnvExperiment):
    
    def build(self):

        ofat_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        ofat_prepare(self)

    def analyze(self):

        ofat_analyze(self)
    
        return

    def run(self):

        # initiate scan

        if self.scan_ok:

            for my_ind in range(len(self.scan_values)):

                self.scheduler.pause()

                # set the new parameter
                scan_parameter(self, my_ind)

        return


