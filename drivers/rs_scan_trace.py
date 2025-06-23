import time
import numpy as np
import matplotlib.pyplot as plt
import datetime
import os

from rs import RS
from keysight_spectrum import Keysight

def create_freq_windows(start_freq, stop_freq, N):

    windows = [0] * N
    boundaries = np.linspace(start_freq, stop_freq, N+1)
    for i in range(N):
        windows[i] = (boundaries[i], boundaries[i+1])

    return windows

if __name__ == '__main__':
    
    ############################
    ##### Experiment setup #####
    ############################
    low_freq = 1000e+06
    high_freq = 2000e+06
    N_windows = 1
    experiment_name = 'Res_test'
    
    ######################################
    ###### Experiment initialization #####
    ######################################
    freq_windows = create_freq_windows(low_freq, high_freq, N_windows)
    print('Frequency Windows:')
    for (f1, f2) in freq_windows:
        print(f'\t{f1/1e6:.1f} MHz to {f2/1e6:.1f} MHz')

    rs = RS()
    spec = Keysight()
    
    rs.on()
        
    ######################
    ##### Experiment #####
    ######################
    start_time = time.time()

    for i, (fmin, fmax) in enumerate(freq_windows):
        print(f'Scanning window {i+1}/{N_windows} ({fmin:.1f} MHz to {fmax:.1f} MHz)')

        fspan = fmax - fmin
        fctr  = (fmin + fmax) / 2
        freq_arr = np.linspace(fmin, fmax, 1001)

        spec.set_center_freq(fctr)
        spec.set_span(fspan)
        spec.set_trace(2, 'WRIT')
        spec.set_trace(2, 'MAXH')
        time.sleep(0.5)

        for j, freq in enumerate(freq_arr):
    
            #print(f' Step {j}/{steps-1}, freq = {freq/1e9:.4f} GHz')
            rs.set_freq(freq)
            #time.sleep(0.05)

        spec.save_trace(2, experiment_name + '_' + str(i+1) + '.csv')
        print('Measurement data saved to spectrum analyzer (not this computer)')
    
    end_time = time.time()
    print(f'Total stepping time: {end_time - start_time:.2f} s')

    rs.off()
    rs.close()
    spec.close()
