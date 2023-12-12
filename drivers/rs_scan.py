import socket
import time
import numpy as np


if __name__ == '__main__':
    
    import matplotlib.pyplot as plt
    
    rs = RS()
    
    spec = Keysight()
    
    
    rs.on()
    
    spec.marker_on(1)
    
    x_arr = []
    y_arr = []
    
    
    
    #low_freq = 1e9
    #high_freq = 2.5e9
    
    my_width = 200e6
    
    cnt_freq = 210e6
    
    low_freq = cnt_freq - my_width
    high_freq = cnt_freq + my_width
    
    
    steps = 4001
    
    
    span_freq = high_freq - low_freq
    cnt_freq = (high_freq + low_freq)/2.0
    
    
    spec.set_center_freq(cnt_freq)
    spec.set_span(span_freq)
    
    
    #spec.set_span(100e6)
    
    
    freq_arr = cnt_freq + np.linspace(-0.5*span_freq,0.5*span_freq,steps)
    
    cnt = 0
    for freq in freq_arr:
    
        print(" Step #: {0} ; Frequency: {1:2.6f} GHz".format(cnt, freq/1e9))
     
        spec.set_center_freq(freq)
    
        rs.set_freq(freq)
    
        (x, y, err) = spec.marker_measure(1, wait_time = 0.2)
    
        print(err)
    
        x_arr.append(x)
        y_arr.append(y)
        
        cnt += 1
    
    rs.off()
    
    rs.close()
    spec.close()
    
    no = 3
    
    f = open('spec_data_x_' + str(no) + '.csv', 'w')
    np.savetxt(f, x_arr, delimiter=",")
    f.close()
    
    f = open('spec_data_y_' + str(no) + '.csv', 'w')
    np.savetxt(f, y_arr, delimiter=",")
    f.close()
    
    
    plt.figure()
    
    plt.plot(x_arr, y_arr)
    
    plt.show()
    
    
    
