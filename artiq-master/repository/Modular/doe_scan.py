from artiq.experiment import EnvExperiment
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import doe_build
from prepare_functions import doe_prepare
from analyze_functions import doe_analyze
from run_functions     import measure
from scan_functions    import set_doe_parameters

class DOEScan(EnvExperiment):

    def build(self):
        
        doe_build(self)
        self.sequence_filename = os.path.abspath(__file__)

        return

    def prepare(self):

        doe_prepare(self)

        return

    def analyze(self):

        doe_analyze(self)

        return

    def run(self):

        if not self.scan_ok:
            return

        if self.utility_mode == "DOE Scan":
            for ind, row in self.setpoints.iterrows():
            
                set_doe_parameters(self, row, ind, self.steps)
                
                try:
                    measure(self, ind)
                except (RTIOOverflow, RTIOUnderflow) as e:
                    print(f"RTIO error, terminating experiment ({e})")
                    entry = {"par": "error", "val": f"{type(e).__name__} at experiment {ind}"}
                    self.config_dict.append(entry)
                    try:
                        self.core.reset()
                    except Exception:
                        pass
                    break

        elif self.utility_mode == "Single Experiment":
            ind = 0
            measure(self, ind, print_result = True)
