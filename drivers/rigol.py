import numpy as np
import time
from base_instruments import base_visa_instrument


# Rigol Spectrum Analyzer

class Rigol_RSA3030(base_visa_instrument):
 
    def __init__(self, IP = '192.168.42.45'):

        # call constructor of parent class
        super().__init__(IP)

        return

    def get_trace(self):

        self.write('*OPC')
        
        self.raw_trace = self.query(':TRACE:DATA? TRACE1')
        
        self.wait_finished()

        self.freq_start = float(self.query(':SENS:FREQUENCY:START?'))
        self.freq_stop  = float(self.query(':SENS:FREQUENCY:STOP?'))

        self.y_data = np.array(self.raw_trace.split(','), dtype = float)
        
        self.x_data = np.linspace(self.freq_start, self.freq_stop, len(self.y_data))

        return np.transpose(np.vstack([self.x_data, self.y_data]))

    def set_freq(self, freq_interval):

        self.write('*OPC')

        self.write(':SENSE:FREQ:START {0:.6f}'.format(freq_interval[0]))
        self.write(':SENSE:FREQ:STOP {0:.6f}'.format(freq_interval[1]))

        self.wait_finished()

        return


# Rigol Function Generator

class Rigol_DSG821(base_visa_instrument):

    def __init__(self, IP = '192.168.42.46'):

        # call constructor of parent class
        super().__init__(IP)

        return

    def set_freq(self, freq):

        self.write(':FREQ {0}MHz'.format(float(freq)))
        
        time.sleep(1)

        return

    def set_level(self, level):

        self.write(':LEV {0}'.format(float(level)))

        return

    def on(self):

        self.write(':OUTP ON')

        return

    def off(self):

        self.write(':OUTP OFF')

        return




##################################################################################################
# Main
##################################################################################################

if __name__ == "__main__":

    import matplotlib.pyplot as plt

    s = Rigol_RSA3030()

    #fg = Rigol_DSG821()

    s.id()

    #fg.id()

    #s.set_freq([1e6, 205e6])
    
    s.set_freq([1e6, 205e6])

    d = s.get_trace()

    s.close()
    #fg.close()

    plt.figure()

    plt.plot(d[:, 0]/1e6, d[:, 1])

    plt.show()



