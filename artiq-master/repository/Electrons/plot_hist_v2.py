'''Zijue Luo: Trying to broadcast real time histogram of the time 
distribution of the MCP events
v2: able to generate histogram, but no reset over time'''

from artiq.experiment import *
import numpy as np

class RTHist_test(EnvExperiment):
    def build(self):
        # Devices we need
        self.setattr_device('core')
        self.setattr_device('ttl3') # read out signals
        self.setattr_device('scheduler')

        # Parameters
        self.setattr_argument('number_of_bins', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('detection_time', NumberValue(default=1000,unit='us',scale=1,ndecimals=0,step=1))

    def prepare(self):
        self.core.reset() # reset the core
        self.set_dataset('bin_times', [], broadcast=True) # use to store timestamps of events
        return
                    
    def make_histogram(self):
        hist_data = np.array(self.get_dataset('bin_times'))
        a, b = np.histogram(hist_data, bins=self.number_of_bins)
        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)

    @kernel
    def run(self):
        while True:
            self.core.break_realtime() # in order to prevent RTIO underflows
            t_start = now_mu() # get the start time
            t_end = self.ttl3.gate_rising(self.detection_time*us) # reading rising edges and return the end time
            tstamp = self.ttl3.timestamp_mu(t_end) # reads the timestamp of one event each time
            while tstamp != -1:
                timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start) # convert machine unit to seconds
                timestamp_us = timestamp * 1e6 # convert seconds to microseconds
                self.append_to_dataset('bin_times', timestamp_us) # store the timestamps in microsecond
#                self.bin_times.append(timestamp_us)
                tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event
#            delay(100*ns)
            self.make_histogram()
            self.set_dataset('bin_times', [], broadcast=True)
