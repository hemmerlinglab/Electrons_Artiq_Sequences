from artiq.experiment import *
import sys

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_functions import base_build, doe_build, doe_prepare

class DOEScan(EnvExperiment):

    def build(self):
        
        doe_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return
    
    def prepare(self):

        doe_prepare(self)

        return
    
    def analyze(self):

        return
    
    def run(self):