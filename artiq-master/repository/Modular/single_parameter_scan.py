from artiq.experiment import EnvExperiment
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import ofat_analyze
from run_functions     import measure
from scan_functions    import scan_parameter

class SingleParamScan(EnvExperiment):

    def build(self):

        ofat_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        ofat_prepare(self)

        return

    def analyze(self):

        ofat_analyze(self)
    
        return

    def run(self):

        # initiate scan

        if not self.scan_ok:
            return

        for ind in range(len(self.scan_values)):
            scan_parameter(self, ind)
            measure(self, ind)

        return
