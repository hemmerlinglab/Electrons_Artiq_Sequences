from artiq.experiment import EnvExperiment
from artiq.coredevice.exceptions import RTIOOverflow, RTIOUnderflow
import sys
import os
import time

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from build_functions   import ofat_build
from prepare_functions import ofat_prepare
from analyze_functions import ofat_analyze
from run_functions     import measure, handle_laser_jump, record_RTIO_error, LaserError
from scan_functions    import scan_parameter

MAX_RTIO_RETRIES = 3
MAX_LASER_RETRIES = 3

class SingleParamScan(EnvExperiment):

    def build(self):
        ofat_build(self)
        self.sequence_filename = os.path.abspath(__file__)

    def prepare(self):
        ofat_prepare(self)

    def analyze(self):
        ofat_analyze(self)

    def run(self):

        if not self.scan_ok:
            return

        validate_422 = True
        if self.scanning_parameter == "frequency_422":
            validate_422 = False

        for ind in range(len(self.scan_values)):

            t0 = time.time()
            rtio_retries = 0
            laser_retries = 0

            # Apply current setpoint
            scan_parameter(self, ind)

            while True:

                # Do experiment
                try: measure(self, ind, validate_422=validate_422)

                # Handle RTIO errors from ARTIQ (e.g. overflow due to unstable MCP amplifier)
                except (RTIOOverflow, RTIOUnderflow) as e:
                    record_RTIO_error(self, ind, e)

                    # Not exceed maximum rtio_retries: retry the experiment for current set point
                    rtio_retries += 1
                    if rtio_retries <= MAX_RTIO_RETRIES:
                        print(f"Retrying ({rtio_retries}/{MAX_RTIO_RETRIES}) ...")
                        continue

                    # Exceed maximum rtio_retries: abort and save
                    print(f"Failed after {MAX_RTIO_RETRIES} trials, terminating experiment ...")
                    return

                except LaserError as e:

                    laser_retries += 1

                    # Save error messages
                    print(f"Laser error ({e})")
                    err = (ind, type(e).__name__, int(e.laser_id))
                    self.err_list.append(err)

                    # Logic for laser error handling, only works for 422 now
                    laser_broken_time = time.time()
                    handle_laser_jump(self, laser_to_fix=int(e.laser_id))
                    laser_fixed_time = time.time()

                    # If we do not want the sequence to resume after laser issue
                    too_long = (laser_fixed_time - laser_broken_time) > 10
                    too_many = laser_retries > MAX_LASER_RETRIES
                    if (self.laser_failure == "raise error") and (too_long or too_many):
                        raise RuntimeError(f"LASER_OFF_{int(e.laser_id)}") from e

                    continue

                # If success, just continue for the next set point
                else: break

            self.mutate_dataset("time_cost", ind, time.time() - t0)
