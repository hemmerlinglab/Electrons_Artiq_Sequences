from artiq.experiment import EnvExperiment
import sys
import os

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import ofat_analyze
from run_functions     import measure
from scan_functions    import scan_parameter

MAX_RETRIES = 3
HOST_SLEEP_S = 5

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

            while True:

                retries = 0

                try:
                    measure(self, ind)

                # Handle RTIO errors from ARTIQ (e.g. overflow due to unstable MCP amplifier)
                except (RTIOOverflow, RTIOUnderflow) as e:

                    # Save error messages
                    print(f"RTIO error ({e})")
                    err = (ind, type(e).__name__)
                    self.err_list.append(err)

                    try:
                        self.core.reset()
                    except Exception:
                        pass

                    time.sleep(HOST_SLEEP_S)
                    retries += 1

                    if retries <= self.MAX_RETRIES:
                        print(f"Retrying ({retries}/{MAX_RETRIES}) ...")
                        continue
                    else:
                        print(f"Failed after {MAX_RETRIES} trials, terminating experiment ...")
                        return

                else:
                    break

        return
