import socket
import time
import numpy as np
import matplotlib.pyplot as plt
import datetime
import os

from rs import RS
from keysight_spectrum import Keysight

if __name__ == '__main__':
    
    ############################
    ##### Experiment setup #####
    ############################
    low_freq = 1000e+06
    high_freq = 2000e+06
    steps = 1001
    #spec_span = None
    experiment_name = 'Test'
    
    ################################
    ##### Exp parameters Setup #####
    ################################
    init_wait_time = 0.5
    wait_time = 0.1
    MAX_ATTEMPTS = 10
    INIT_POINTS = 6
    
    init_min = -85
    init_max = +23
    running_min = -85
    thres_min = 0.25
    thres_coeff = 6.25
    
    ##########################
    ##### Error Handling #####
    ##########################
    class RescanAll(Exception):
        def __init__(self, message):
    	    super().__init__(message)
    
    #####################################
    ##### Experiment initialization #####
    #####################################
    rs = RS()
    spec = Keysight()
    
    rs.on()
    spec.marker_on(1)
    
    span_freq = high_freq - low_freq
    cnt_freq = (high_freq + low_freq)/2.0
    freq_arr = np.linspace(low_freq, high_freq, steps)
    
    spec.set_center_freq(cnt_freq)
    #if spec_span is not None: spec.set_span(spec_span)
    #else: spec.set_span(span_freq)
    spec.set_span(span_freq)
    
    ######################
    ##### Experiment #####
    ######################
    start_time = time.time()
    
    x_arr = np.zeros(steps)
    y_arr = np.zeros(steps)
    
    # Main Sequence
    while True:
        try:
            for i, freq in enumerate(freq_arr):

                print(" Step #: {0} ; Frequency: {1:2.6f} GHz".format(i, freq/1e9))

                #if spec_span is not None:
                    #spec.set_center_freq(freq)
                rs.set_freq(freq)
        
                if i < INIT_POINTS:
                    while True:
                        (x, y, err) = spec.marker_measure(1, wait_time = init_wait_time)
                        print(f'Measured Frequenct: {x/1e+09:.3f} GHz\tAmplitude: {y:.2f} dBm.')
                        if (y > init_min and y < init_max):
                            x_arr[i] = x
                            y_arr[i] = y
                            break
                        else: print('Abnormal value, retrying ...')

                else:
                    for attempt in range(MAX_ATTEMPTS):
                        (x, y, err) = spec.marker_measure(1, wait_time = wait_time)
                        print(f'Measured Frequency: {x/1e+09:.3f} GHz\tAmplitude: {y:.2f} dBm.')
                        threshold = max(thres_min, thres_coeff * np.abs(y_arr[i-5:i] - y_arr[i-6:i-1]).sum())
                        if (abs(y - y_arr[i-1]) < threshold and y > running_min): break
                        else:
                            print(y, y_arr[i-1], threshold)
                            print('Abnormal value, Retrying ...')
                    else: raise RescanAll(f'Abnormality persists on frequency {x/1e+09:.3f} GHz, rescanning all ...')
                    x_arr[i] = x
                    y_arr[i] = y

            break # No abnormality on all frequencies, break the while True loop

        except RescanAll as e:
            print(e)
            x_arr = np.zeros(steps)
            y_arr = np.zeros(steps)
            continue
    
    rs.off()
    
    rs.close()
    spec.close()
    
    end_time = time.time()
    print(f'Total time consumption: {end_time - start_time:.2f}')
    
    ################################
    ##### Save experiment data #####
    ################################
    timestamp = datetime.datetime.today()
    folder = 'data/' + timestamp.strftime('%Y%m%d')
    if not os.path.exists(folder):
        os.makedirs(folder)
    basefilename = folder + '/' + experiment_name
    
    f = open(basefilename + '_x.csv', 'w')
    np.savetxt(f, x_arr, delimiter=",")
    f.close()
    
    f = open(basefilename + '_y.csv', 'w')
    np.savetxt(f, y_arr, delimiter=",")
    f.close()
    
    ##########################
    ##### Result preview #####
    ##########################
    plt.figure()
    plt.plot(x_arr, y_arr)
    plt.title(experiment_name)
    plt.xlabel('Frequency')
    plt.ylabel('Response')
    plt.show()

