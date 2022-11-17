from artiq.experiment import *
import numpy as np


class sync_test(EnvExperiment):

    def build(self):
        # Devices we need
        self.setattr_device('core')
        self.setattr_device('ttl3') # read out signals
        self.setattr_device('ttl8') # read out signals
        self.setattr_device('ttl11') # read out signals
        self.setattr_device('scheduler')

        # Parameters
        self.setattr_argument('number_of_bins', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('detection_time', NumberValue(default=1000,unit='us',scale=1,ndecimals=0,step=1))
        self.setattr_argument('max_loop_data', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))

    def prepare(self):
        self.core.reset() # reset the core
        self.set_dataset('bin_times', [0], broadcast=True) # use to store timestamps of events, place 0 to be consistent with reset code
        self.hist_data = [] # use to store timestamp datas of up to max_loop_data times
        return
                    
    def make_histogram(self, loop):
        extract = list(self.get_dataset('bin_times'))

        # use extract[1:len(extract)] to discard the 0 placed when doing initilization and reset
        if loop < self.max_loop_data:
            self.hist_data.append(extract[1:len(extract)])
        else:
            self.hist_data[loop % self.max_loop_data] = extract[1:len(extract)]
        
        flatten_data = sum(self.hist_data, []) # flatten 2D list self.hist_data to 1D list
        a, b = np.histogram(flatten_data, bins = np.linspace(0, self.detection_time, self.number_of_bins))
        
        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)

    @kernel
    def read_timestamps(self, t_start, t_end, loop):
        tstamp = self.ttl3.timestamp_mu(t_end)
        while tstamp != -1:
            timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
            timestamp_us = timestamp * 1e6
            self.append_to_dataset('bin_times', timestamp_us) # store the timestamps in microsecond
            tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

        self.make_histogram(loop)
        self.set_dataset('bin_times', [0], broadcast=True) # reset with empty list is not allowed, so place a zero in it
        return

    @kernel
    def get_counts(self):
        
        loop = 0
        while True:
            self.core.break_realtime() # in order to prevent RTIO underflows

            # codes for testing: triggering function generator to send test pulses
            self.ttl8.pulse(1*us)
            self.ttl11.pulse(1*us)

            t_start = now_mu() # get the start time
            t_end = self.ttl3.gate_rising(self.detection_time*us) # reading rising edges and return the end time
            self.read_timestamps(t_start, t_end, loop)
            loop += 1

        return

    def run(self):
        
        self.scheduler.pause() # allows for "terminate instances" functionality
        self.get_counts()

