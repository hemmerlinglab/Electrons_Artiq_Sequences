from artiq.language.core import TerminationRequested
from artiq.coredevice.exceptions import RTIOOverflow, RTIOUnderflow
import numpy as np
import time
from scipy.optimize import curve_fit

from base_sequences import (
    count_histogram,
    count_events,
    record_laser_frequencies,
    bare_counting,
    record_RF_amplitude,
    set_multipoles,
    sampler_read,
    recover_threshold_detector
)
from helper_functions import latin_hypercube, bo_suggest_next

# gailezheli
from scan_functions import _scan_wait_time


MAX_RTIO_RETRIES = 3
MAX_LASER_RETRIES = 3
MAX_DETECTOR_RETRIES = 5

# ===================================================================
# 0) Customized Errors for Laser Jump and Detector Anomly
class LaserError(RuntimeError):
    def __init__(self, laser_id: int, message: str = None, actual=None, setpoint=None):
        self.laser_id = int(laser_id)
        self.actual = actual
        self.setpoint = setpoint
        if message is None:
            message = f"Laser frequency of {self.laser_id} is off, please fix it manually!"
        super().__init__(message)

class DetectorError(RuntimeError):
    pass

# ===================================================================
# 1) Master Functions for Run (For Experiment)
def run_experiment_with_retries(self, experiment_function, ind, **kwargs):
    """
    experiment_function: `measure` or `bo_sampling`
    """
    # Initialize number of retries
    rtio_retries     = 0
    laser_retries    = 0
    detector_retries = 0

    while True:

        # Perform Experiments
        try:
            return experiment_function(self, ind, **kwargs)

        # Handle RTIO Errors
        except (RTIOOverflow, RTIOUnderflow) as e:
            record_RTIO_error(self, ind, e)
            rtio_retries += 1
            if rtio_retries <= MAX_RTIO_RETRIES:
                print(f"Retrying ({rtio_retries}/{MAX_RTIO_RETRIES}) ...")
                continue
            print(f"Failed after {MAX_RTIO_RETRIES} trials, terminating experiment ...")
            raise RuntimeError("Unable to address RTIO error!")

        # Handle Laser Errors
        except LaserError as e:
            record_laser_error(self, ind, e)
            laser_retries += 1
            t0 = time.time()
            handle_laser_jump(self, laser_to_fix=int(e.laser_id))
            dt = time.time() - t0
            too_long = dt > 10
            too_many = laser_retries > MAX_LASER_RETRIES
            if (self.laser_failure == "raise error") and (too_long or too_many):
                raise RuntimeError(f"LASER_OFF_{int(e.laser_id)}") from e
            continue

        except DetectorError as e:
            record_detector_error(self, ind, e)
            detector_retries += 1
            ok = recover_threshold_detector(self)
            if ok:
                print(f"Recovered detector, Retrying ({detector_retries}/{MAX_DETECTOR_RETRIES}) ...")
                continue
            if detector_retries <= MAX_DETECTOR_RETRIES:
                print(f"Failed to recover detector, Retrying ({detector_retries}/{MAX_DETECTOR_RETRIES}) ...")
            raise RuntimeError("Unable to address detector error!")

        except TerminationRequested as e:
            print("Termination requested, aborting the experiment ...")
            raise TerminationRequested(e) from e

# ===================================================================
# 1) Top Level Controllers
def measure(self, ind, print_result=False, validate_390=False, validate_422=True,
            expected_freq_422=None, expected_freq_390=None):

    if self.scheduler.check_pause():
        raise TerminationRequested("Termination requested during scan")

    if self.RF_amp_mode == "locked":
        self.rf.set_amplitude()

    status_390, status_422 = record_laser_frequencies(
        self, ind, target_422=expected_freq_422, target_390=expected_freq_390
    )
    record_RF_amplitude(self, ind)

    # Validate laser frequencies (compare actual vs expected setpoint)
    if validate_390 and not status_390:
        raise LaserError(390)
    if validate_422 and not status_422:
        raise LaserError(422)

    if self.mode == "Trapping":
        if self.histogram_on:
            cts_trapped, cts_lost, cts_loading = trap_with_histogram(self, ind)
        else:
            cts_trapped, cts_lost, cts_loading = trap_without_histogram(self)

        store_to_dataset(self, ind, cts_trapped, cts_lost, cts_loading)

        if print_result:
            print(f"Trapped: {cts_trapped}, Lost: {cts_lost}, Loading: {cts_loading}")

# 改了這裡
    elif self.mode == 'Lifetime_fast':
        N = np.zeros(2)

        for i, wt in enumerate([0.0, self.wait_time_fast]):
            _scan_wait_time(self, wt, None)

            if self.histogram_on:
                cts_trapped, cts_lost, cts_loading = trap_with_histogram(self, 2*ind+i)
            else:
                cts_trapped, cts_lost, cts_loading = trap_without_histogram(self)

            store_to_dataset(self, 2*ind+i, cts_trapped, cts_lost, cts_loading)

            if cts_loading == 0:
                raise RuntimeError("No Loading Signal Detected")

            N[i] = cts_trapped/cts_loading

        # compute lifetime function
        lifetime_fast = self.wait_time_fast/np.log(N[0]/N[1])

        self.mutate_dataset('lifetime', ind, lifetime_fast)


    elif self.mode == 'Lifetime':
        n = len(self.wait_time_arr)
        N = np.zeros(n)

        for i, wt in enumerate(self.wait_time_arr):
            _scan_wait_time(self, wt, None)
            self.no_of_repeats = int(self.repeats_arr[i])

            if self.histogram_on:
                cts_trapped, cts_lost, cts_loading = trap_with_histogram(self, n*ind+i)
            else:
                cts_trapped, cts_lost, cts_loading = trap_without_histogram(self)

            store_to_dataset(self, n*ind+i, cts_trapped, cts_lost, cts_loading)

            if cts_loading == 0:
                raise RuntimeError("No Loading Signal Detected")

            N[i] = cts_trapped/cts_loading

        # fit for lifetime
        def f(t, N0, tao):
            y = N0*np.exp(-t/tao)
            return y

        # Point 0 for initial estimation
        idx0 = np.argmin(self.wait_time_arr)
        N0 = N[idx0]
        t0 = self.wait_time_arr[idx0]

        # Point 1 for initial estimation
        target = np.min(self.wait_time_arr) + self.wait_time_fast
        idx1 = np.abs(self.wait_time_arr - target).argmin()
        N1 = N[idx1]
        t1 = self.wait_time_arr[idx1]
        tao0 = (t1-t0)/np.log(N0/N1)

        popt, pcov = curve_fit(f, self.wait_time_arr, N, p0=[N0*np.exp(t0/tao0), tao0], bounds=((0, 0), (np.inf, np.inf)))

        tao = popt[1]
        self.mutate_dataset('lifetime', ind, tao)


    elif self.mode == 'Counting':
        # Counting mode information sheet:
        # laser: Controlled
        # tickle: As long as `tickle_on` was set to off, it would be fine
        # RF Drive: Kept off
        # DC multipoles: Controlled, so set to 0 if not wanted
        # extraction pulse: Not triggered
        # mesh: Controlled
        # MCP front: Controlled
        
        # Tips:
        # 1. I know RF could increase electron count, but I would prefer not
        #     to introduce extra attributes now, so turn it on from code if you
        #     really need it, or just add this attribute if you want.

        cts = bare_counting(self)
        self.mutate_dataset('scan_result', ind, cts)

        if print_result:
            print(f"Recorded Number of electrons: {cts}")

    return 0

def record_RTIO_error(self, ind, err):

    # constant
    HOST_SLEEP_S = 5

    # Save errror messages
    print(f"RTIO error ({err})")
    err = (ind, type(err).__name__)
    self.err_list.append(err)

    # Reset ArtiQ coredevice
    self.core.reset()

    # Wait for a period of time
    # e.g. wait for the unstable amplifier behavior to disappear
    time.sleep(HOST_SLEEP_S)

def record_laser_error(self, ind, err):
    print(f"Laser error ({err})")
    err = (ind, type(err).__name__)
    self.err_list.append(err)

def record_detector_error(self, ind, err):
    print(f"Detector error ({err})")
    err = (ind, type(err).__name__)
    self.err_list.append(err)

def handle_laser_jump(self, laser_to_fix = 422, tol = 1e-5):
    """
    When laser frequency was off (mode hopping), wait for the user to fix it manually.
    """

    act_freq = self.laser.get_frequency(laser_to_fix)
    setpoint = getattr(self, f"frequency_{laser_to_fix}")

    while abs(act_freq - setpoint) > tol:

        if self.scheduler.check_pause():
            raise TerminationRequested("Termination requested during laser jump handling")

        time.sleep(1.0)
        act_freq = self.laser.get_frequency(laser_to_fix)

# ===================================================================
# 2) For Optimizer
def initial_sampling(self):

    init_points = latin_hypercube(self.init_sample_size, self.bounds)

    for ind, pt in enumerate(init_points):
        t0 = time.time()
        run_experiment_with_retries(self, measure_optimize, ind, E_field=pt)
        self.mutate_dataset("time_cost", ind, time.time() - t0)

def bo_sampling(self, ind):

    # calculate the next point to measure
    E_next, ei, params = bo_suggest_next(
        self.E_sampled, self.y_sampled, self.bounds,
        n_candidates=self.n_candidate_run
    )

    # perform experiment
    measure_optimize(self, ind + self.init_sample_size, E_next)

    # store BO result
    self.mutate_dataset("y_best", ind, np.max(self.y_sampled))
    self.mutate_dataset("ei", ind, ei)

    # store BO parameters
    self.mutate_dataset("length_scale", ind, params[0])
    self.mutate_dataset("best_rel_noise", ind, params[1])

    return ei

def measure_optimize(self, ind, E_field=None):

    # implement setpoint
    self.Ex, self.Ey, self.Ez = E_field
    set_multipoles(self)

    # perform measurement
    signal = trap_optimize(self, ind)

    # store result
    self.E_sampled.append(E_field)
    self.y_sampled.append(signal)
    self.mutate_dataset("e_trace", ind, E_field)

def trap_optimize(self, ind):

    if self.scheduler.check_pause():
        raise TerminationRequested("Termination requested during scan")

    # Record Laser and RF data
    status_390, status_422 = record_laser_frequencies(self, ind)
    record_RF_amplitude(self, ind)

    if self.histogram_on:
        cts_trapped, cts_lost, cts_loading = trap_with_histogram(self, ind)
    else:
        cts_trapped, cts_lost, cts_loading = trap_without_histogram(self)

    store_to_dataset(self, ind, cts_trapped, cts_lost, cts_loading)

    if self.optimize_target == "trapped_signal":
        signal = cts_trapped
    elif self.optimize_target == "ratio_signal":
        ssignal = (cts_trapped / cts_loading) if cts_loading > 0 else 0.0
    elif self.optimize_target == "ratio_weighted":
        signal = ((cts_trapped + 2 * cts_lost) / cts_loading) if cts_loading > 0 else 0.0
    elif self.optimize_target == "lost_signal":
        signal = cts_lost
    elif self.optimize_target == "ratio_lost":
        signal = (cts_lost / cts_loading) if cts_loading > 0 else 0.0
    elif self.optimize_target == "loading_signal":
        signal = cts_loading
    else:
        raise RuntimeError("Optimize target not supported!")
    
    print(f"{ind:2d}/{self.init_sample_size + self.max_iteration}: E=({self.Ex:.3f},\t{self.Ey:.3f},\t{self.Ez:.3f}):\tsignal={signal:.3f}")
    return signal

# ===================================================================
# 3) Basic Components
def trap_with_histogram(self, my_ind):

    # run detection sequence
    count_histogram(self)

    # get result
    xs = self.get_dataset('hist_xs')
    ys = self.get_dataset('hist_ys')
    self.mutate_dataset('arr_of_timestamps', my_ind, self.get_dataset('timestamps'))

    # calculate trapped count
    ind_l = (xs > (self.load_time + self.wait_time - 1))[:-1]
    ind_u = (xs < (self.load_time + self.wait_time + self.ext_pulse_length // 1000 + 3))[:-1]
    cts_trapped = np.sum(ys[ind_l*ind_u])

    # calculate kicked out count
    ind_l = (xs > (self.load_time + 4))[:-1]
    ind_u = (xs < (self.load_time + self.tickle_pulse_length + 3))[:-1]
    #print(ys[ind_l*ind_u])
    cts_lost = np.sum(ys[ind_l*ind_u])

    # calculate loading count
    ind_l = (xs > 1)[:-1]
    ind_u = (xs < (self.load_time + 2))[:-1]
    cts_loading = np.sum(ys[ind_l*ind_u])

    return cts_trapped, cts_lost, cts_loading

def trap_without_histogram(self):

    # run detection sequence
    count_events(self)

    # get result
    events = np.array(self.get_dataset('timestamps'))
    cts_loading = len(events[events<(self.load_time + 2)])
    cts_trapped = len(events[events>(self.load_time + self.wait_time -3)])
    cts_lost = 0

    return cts_trapped, cts_lost, cts_loading

def store_to_dataset(self, my_ind, cts_trapped, cts_lost, cts_loading):

    # store result
    self.mutate_dataset('trapped_signal', my_ind, cts_trapped)
    self.mutate_dataset('lost_signal', my_ind, cts_lost)
    self.mutate_dataset('loading_signal', my_ind, cts_loading)

    # calculate ratios
    if cts_loading > 0:
        self.mutate_dataset('ratio_signal', my_ind, cts_trapped / cts_loading)
        self.mutate_dataset('ratio_lost', my_ind, cts_lost / cts_loading)
    else:
        self.mutate_dataset('ratio_signal', my_ind, 0.0)
        self.mutate_dataset('ratio_lost', my_ind, 0.0)

    # reset timestamps
    self.set_dataset('timestamps', [], broadcast=True)
    self.set_dataset('timestamps_loading', [], broadcast=True)

    # handle threshold detector errors
    if cts_loading == 0:
        qbar = sampler_read(self)[4]
        if qbar <= 0.5:
            raise DetectorError("Threshold detector was dead!")
