import numpy as np
import sys
import time

from base_sequences import count_histogram, count_events, record_laser_frequencies, bare_counting, set_multipoles

# ===================================================================
# 1) Master Functions for Run (For Experiment)
def measure(self, ind, print_result = False):

    self.scheduler.pause()

    t0 = time.time()
    record_laser_frequencies(self, ind)

    if self.mode == "Trapping":
        if self.histogram_on:
            cts_trapped, cts_lost, cts_loading = trap_with_histogram(self, ind)
        else:
            cts_trapped, cts_lost, cts_loading = trap_without_histogram(self, ind)

        store_to_dataset(self, ind, cts_trapped, cts_lost, cts_loading)

        if print_result:
            print(f"Trapped: {cts_trapped}, Lost: {cts_lost}, Loading: {cts_loading}")

    elif self.mode == 'Counting':
        """
        Counting mode information sheet:
        laser: Controlled
        tickle: As long as `tickle_on` was set to off, it would be fine
        RF Drive: Kept off
        DC multipoles: Controlled, so set to 0 if not wanted
        extraction pulse: Not triggered
        mesh: Controlled
        MCP front: Controlled
        
        Tips:
        1. I know RF could increase electron count, but I would prefer not
            to introduce extra attributes now, so turn it on from code if you
            really need it, or just add this attribute if you want.
        """

        cts = bare_counting(self)
        self.mutate_dataset('scan_result', ind, cts)

        if print_result:
            print(f"Recorded Number of electrons: {cts}")

    # time cost tracker
    self.mutate_dataset('time_cost', ind, time.time() - t0)

    return

# ===================================================================
# 2) For Optimizer
def backtracking_ascent(self, current_step):

    return

def get_gradient(self, current_step):

    self.mutate_dataset('e_trace', current_step, self.current_E)
    
    this_module = sys.modules[__name__]
    grad_func = getattr(this_module, f"gradient_{self.method}")
    gradient, fc = grad_func(self, current_step)
  
    return gradient, fc

def gradient_central(self, current_step):

    I = np.eye(3)
    g = np.zeros(3, dtype=float)
    h = self.diff_step
    ind = current_step * 7
    fc = 0

    for k in range(3):

        # Forward Point
        self.Ex, self.Ey, self.Ez = self.current_E + h * I[k]
        set_multipoles(self)
        fp = trap_optimize(self, ind)
        ind += 1

        # Backward Point
        self.Ex, self.Ey, self.Ez = self.current_E - h * I[k]
        set_multipoles(self)
        fm = trap_optimize(self, ind)
        ind += 1

        # Calculate Derivative
        g[k] = (fp - fm) / (2 * h)

        # Accumulate fc
        fc += fp + fm

    return g, fc / 6

def gradient_forward(self, current_step):

    I = np.eye(3)
    g = np.zeros(3, dtype=float)
    h = self.diff_step
    ind = current_step * 5

    # Center Point
    self.Ex, self.Ey, self.Ez = self.current_E
    set_multipoles(self)
    fc = trap_optimize(self, ind)
    ind += 1

    for k in range(3):
        self.Ex, self.Ey, self.Ez = self.current_E + h * I[k]
        set_multipoles(self)
        fp = trap_optimize(self, ind)
        ind += 1

        g[k] = (fp - fc) / h

    return g, fc

def trap_optimize(self, ind):

    self.scheduler.pause()

    t0 = time.time()

    if self.histogram_on:
        cts_trapped, cts_lost, cts_loading = trap_with_histogram(self, ind)
    else:
        cts_trapped, cts_lost, cts_loading = trap_without_histogram(self, ind)

    store_to_dataset(self, ind, cts_trapped, cts_lost, cts_loading)
    
    self.mutate_dataset('time_cost', ind, time.time() - t0)

    if self.optimize_target == "trapped_signal":
        return cts_trapped
    elif self.optimize_target == "ratio_signal":
        return cts_trapped / cts_loading
    elif self.optimize_target == "lost_signal":
        return cts_lost
    elif self.optimize_target == "ratio_lost":
        return cts_lost / cts_loading
    elif self.optimize_target == "loading_signal":
        return cts_loading
    else:
        raise RuntimeError("Optimize target not supported!")

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
    print(ys[ind_l*ind_u])
    cts_lost = np.sum(ys[ind_l*ind_u])

    # calculate loading count
    ind_l = (xs > 1)[:-1]
    ind_u = (xs < (self.load_time + 2))[:-1]
    cts_loading = np.sum(ys[ind_l*ind_u])

    return cts_trapped, cts_lost, cts_loading

def trap_without_histogram(self, my_ind):

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

    return
