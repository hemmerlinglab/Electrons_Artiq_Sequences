from artiq.experiment import *
import sys

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_functions import base_build, doe_build

class DOEScan(EnvExperiment):

    def build(self):
        
        doe_build(self)
        base_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return