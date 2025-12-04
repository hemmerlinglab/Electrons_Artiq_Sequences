from artiq.experiment import EnvExperiment
from artiq.coredevice.exceptions import RTIOOverflow, RTIOUnderflow
import sys
import os
import time

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import doe_build
from prepare_functions import doe_prepare
from analyze_functions import doe_analyze
from run_functions     import measure, handle_laser_jump, record_RTIO_error
from scan_functions    import set_doe_parameters

MAX_RETRIES = 3

class DOEScan(EnvExperiment):

    def build(self):
        doe_build(self)
        self.sequence_filename = os.path.abspath(__file__)

    def prepare(self):
        doe_prepare(self)

    def analyze(self):
        doe_analyze(self)

    def run(self):

        if not self.scan_ok:
            return

        if self.utility_mode == "DOE Scan":

            for ind, row in self.setpoints.iterrows():

                t0 = time.time()
                retries = 0

                # Apply current setpoint
                set_doe_parameters(self, row, ind, self.steps)

                while True:

                    # Do experiment
                    try: measure(self, ind)

                    # Handle RTIO errors from ARTIQ (e.g. overflow due to unstable MCP amplifier)
                    except (RTIOOverflow, RTIOUnderflow) as e:
                        record_RTIO_error(self, ind, e)

                        # Not exceed maximum retries: retry the experiment for current set point
                        retries += 1
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

        elif self.utility_mode == "Single Experiment":

            ind = 0
            
            while True:
                try:
                    measure(self, ind, print_result=True)
                except (RTIOOverflow, RTIOUnderflow) as e:
                    print(f"RTIO error ({e})")
                    self.core.reset()
                    continue
                else:
                    break
