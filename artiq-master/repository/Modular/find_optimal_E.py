from artiq.experiment import EnvExperiment
import numpy as np
import time
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import optimizer_build
from prepare_functions import optimizer_prepare
from run_functions     import get_gradient

class FindOptimalE(EnvExperiment):

    def build(self):

        optimizer_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        optimizer_prepare(self)

        return

    def analyze(self):

        return

    def run(self):

        if not self.scan_ok:
            return
        
        t_start = time.time()
        
        for current_step in range(self.max_iteration):

            gradient, center_value = get_gradient(self, current_step)
            g_norm = np.linalg.norm(gradient, ord=np.inf)
            
            if g_norm < self.rtol * center_value + self.atol:
                break
        