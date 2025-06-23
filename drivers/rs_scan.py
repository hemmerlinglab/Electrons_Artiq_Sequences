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
    spec_span = 10e+06
    experiment_name = 'Mesh1_feed_T'
    
    ######################################
    ###### Experiment initialization #####
    ######################################
    rs = RS()
    spec = Keysight()
    
    rs.on()
    spec.marker_on(1)
    
    span_freq = high_freq - low_freq
    cnt_freq = (high_freq + low_freq)/2.0
    freq_arr = np.linspace(low_freq, high_freq, steps)
    
    spec.set_center_freq(cnt_freq)
    if spec_span is not None: spec.set_span(spec_span)
    else: spec.set_span(span_freq)
    
    ######################
    ##### Experiment #####
    ######################
    start_time = time.time()
    
    x_arr = np.zeros(steps)
    y_arr = np.zeros(steps)
    
    for i, freq in enumerate(freq_arr):
    
        print(" Step #: {0} ; Frequency: {1:2.6f} GHz".format(i, freq/1e9))
     
        spec.set_center_freq(freq)
        rs.set_freq(freq)
        
        if i < 6:
            while True:
                (x, y, err) = spec.marker_measure(1, wait_time = 0.5)
                print(f'Measured Frequenct: {x/1e+09:.3f} GHz\tAmplitude: {y:.2f} dBm.')
                if (y > -80 and y < 30): break
                else: print('Abnormal value, retrying ...') 
        else:
            while True:
                (x, y, err) = spec.marker_measure(1, wait_time = 0.1)
                print(f'Measured Frequenct: {x/1e+09:.3f} GHz\tAmplitude: {y:.2f} dBm.')
                threshold = max(0.25, 6.25 * np.sqrt((y_arr[i-5:i] - y_arr[i-6:i-1])**2).sum())
                if (abs(y - y_arr[i-1]) < threshold and y > -80): break
                else:
                    print(y, y_arr[i-1], threshold)
                    print('Abnormal value, Retrying ...')
        
        x_arr[i] = x
        y_arr[i] = y
    
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

