''' Differences from V2: 
	Goal: count rate vs time
	- within detection time, count the number of pulses within time block
	- make number of pulses counted N
	- make a dot on the live feed at the moment of N/detection time   
 '''

import sys
import os
#import datetime import datetime
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np

#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')


# Class which defines the pmt counting experiment
class pulse_counting3(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         self.setattr_device('scheduler') # scheduler used
		# set arguments that can be varied on the dashboard 
         self.setattr_argument('detection_time',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1))
    def prepare(self):
		# this function runs before the experiment, set dataset variables here
		#self.set_dataset('counts/detection time', )
        pass 
    def run(self):
        self.core.reset()
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            self.run_pmt()
   
    # run_pmt, this is directly counting pulses in FPGA and decorated with kernel so that artiq is listening/waiting for a pulse for 100ms        
    @kernel
    def run_pmt(self):
        t_count = self.ttl3.gate_rising(self.detection_time*ms)
        self.core.break_realtime()
        pmt_count = self.ttl3.count(t_count)
        self.pc(pmt_count)
    #prints the counts, decorated with rpc because this is something computer does, do not want to wait for artiq to count before going to next line, want to do it simultaneously  
    @rpc(flags={"async"}) 
    def pc(self,counts): 
        print(counts)

