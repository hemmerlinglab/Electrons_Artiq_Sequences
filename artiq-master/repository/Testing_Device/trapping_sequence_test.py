'''Zijue Luo: Used to debug the trapping sequence and resolves underflows'''

from artiq.experiment import *
import numpy as np
from time import time

class Trapping_test(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('ttl3')
        self.setattr_device('ttl6')
        self.setattr_device('ttl9')
        self.setattr_device('ttl10')

        self.setattr_argument('mode', EnumerationValue(['kernel run', 'PC run'],default='kernel run'))
        self.setattr_argument('detection_time', NumberValue(default=50,unit='us',scale=1,ndecimals=0,step=1))
        self.setattr_argument('number_of_bins', NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1))


    def prepare(self):

        self.set_dataset('bin_times', [0], broadcast=True)
        self.hist_data = []
        self.core.reset()


    def make_histogram(self):

        extract = list(self.get_dataset('bin_times'))
        self.hist_data.append(extract[1:len(extract)])
        
        flatten_data = sum(self.hist_data, []) # flatten 2D list self.hist_data to 1D list
        a, b = np.histogram(flatten_data, bins = np.linspace(0, self.detection_time, self.number_of_bins))
        
        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)

        return


    @kernel
    def read_timestamps(self, t_start, t_end):
        tstamp = self.ttl3.timestamp_mu(t_end)
        while tstamp != -1:
            timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
            timestamp_us = timestamp * 1e6
            self.append_to_dataset('bin_times', timestamp_us) # store the timestamps in microsecond
            tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

        self.make_histogram()
        self.set_dataset('bin_times', [0], broadcast=True) # reset with empty list is not allowed, so place a zero in it
        return




    @kernel
    def called_sequence(self):

        self.core.break_realtime()
        
        with parallel:
            with sequential:
                t_start = now_mu()
                t_end = self.ttl3.gate_rising(self.detection_time*us)
            with sequential:
                self.ttl6.pulse(1*us)
                delay(9*us)
                self.ttl9.pulse(1*us)
                delay(9*us)
                self.ttl10.pulse(20*ns)
                delay(29*us)

        self.read_timestamps(t_start, t_end)

#    @kernel
    def run(self):

        if self.mode == 'kernel run':

            # Time test result (without breaking realtime): RTIO underflow
            # Time test result (breaks realtime): 4.2 ms per loop
            for i in range(10000):
#            while True:

#                self.core.break_realtime()

                with parallel:
                    with sequential:
                        t_start = now_mu()
                        t_end = self.ttl3.gate_rising(self.detection_time*us)
                    with sequential:
                        self.ttl6.pulse(1*us)
                        delay(9*us)
                        self.ttl9.pulse(1*us)
                        delay(9*us)
                        self.ttl10.pulse(20*ns)
                        delay(29*us)

                self.read_timestamps(t_start, t_end)

            print('Done!')

        else:
#            t_start = time()
            # Time test result: 160 ms per loop
            for i in range(100):

#                t_start = time()

                self.called_sequence()

            print('Done!')

