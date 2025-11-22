from artiq.experiment import EnvExperiment
from artiq.coredevice.exceptions import RTIOOverflow, RTIOUnderflow
import sys
import os
import time

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import ofat_analyze
from run_functions     import measure, handle_laser_jump
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

            t0 = time.time()
            retries = 0

            # Apply current setpoint
            scan_parameter(self, ind)

            while True:

                # Do experiment
                try: measure(self, ind)

                # Handle RTIO errors from ARTIQ (e.g. overflow due to unstable MCP amplifier)
                except (RTIOOverflow, RTIOUnderflow) as e:

                    # Save error messages
                    print(f"RTIO error ({e})")
                    err = (ind, type(e).__name__)
                    self.err_list.append(err)

                    # Reset ArtiQ coredevice
                    self.core.reset()

                    # Wait for a period of time (e.g. wait for the unstable amplifier behavior to disappear)
                    time.sleep(HOST_SLEEP_S)
                    retries += 1

                    # Not exceed maximum retries: retry the experiment for current set point
                    if retries <= MAX_RETRIES:
                        print(f"Retrying ({retries}/{MAX_RETRIES}) ...")
                        continue

                    # Exceed maximum retries: abort and save
                    print(f"Failed after {MAX_RETRIES} trials, terminating experiment ...")
                    return

                except RuntimeError as e:

                    # Save error messages
                    print(f"Laser error ({e})")
                    err = (ind, type(e).__name__)
                    self.err_list.append(err)

                    # Logic for laser error handling, only works for 422 now
                    handle_laser_jump(self)

                # If success, just continue for the next set point
                else: break

            self.mutate_dataset("time_cost", ind, time.time() - t0)

        return
