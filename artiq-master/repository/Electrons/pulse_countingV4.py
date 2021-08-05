''' Differences from V2: 
        Runs: displays the counts, but the counts are wrong, 

        Goal: count rate vs time
	- within detection time, count the number of pulses within time block
	- make number of pulses counted N
	- make a dot on the live feed at the moment of N/detection time   
 Tried to accomplish: making a time axis similar to the scope count code to be able to display live view of the counts

Todo: store number of counts in a list from ttl port to be displayed on live feed
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


#def pc(self,counts): 
#    print(counts)

# Class which defines the pmt counting experiment
class pulse_counting3(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         # set arguments that can be varied on the dashboard 
         
         self.setattr_argument('step_size',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1)) #time scale on the scope,how zoomed you are in time
    
         self.setattr_argument('time_count', NumberValue(default=400,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used
    def prepare(self):
	# this function runs before the experiment, set dataset variables here
        self.time_interval=np.linspace(0,(self.step_size)*(self.time_count-1)/1.0e3,self.time_count)
        self.set_dataset('times',(self.time_interval),broadcast=True)
    def run(self):
        self.core.reset()
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
         #   delay(100*ms)
            self.run_pmt()
        #    delay(100*ms)
   
    # run_pmt, this is directly counting pulses in FPGA and decorated with kernel so that artiq is listening/waiting for a pulse for 100ms        
    @kernel
    def run_pmt(self):
        self.core.break_realtime()

        # read the counts and store into a dataset
        
        # single step in time
        data0 = [0]*self.time_count

        # define a count variable and continuously override
        #count = [0]

        # continuously override 
        for j in range(self.time_count):

            data0[j]=self.ttl3.gate_rising(self.detection_time*ms) # reads from the channel
            #data0[j] = count[0]
            # delay for as long your listening for, translates between machine time and actual time
            delay(self.detection_time*ms)
        
        self.set_dataset('TTL_counts',(data0),broadcast=True)
        



