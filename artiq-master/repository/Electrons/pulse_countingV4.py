''' Differences from V3: 
 - added a variable count to count properly

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
class pulse_counting4(EnvExperiment):
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
        #self.ttl3.init() #initializes sampler

        # read the counts and store into a dataset
        
        # single step in time, defines the length of the list as the time count
        count_tot = [0]*self.time_count

        # save the number of counts into a variable called data0
        for j in range(self.time_count):
            #register rising edges for detection time
            t_count= self.ttl3.gate_rising(self.detection_time*ms) # reads from the channel
            count =self.ttl3.count(t_counts)
            self.mutate_dataset('count_tot',j,count)
            # delay for as long your listening for, translates between machine time and actual time
            delay(self.detection_time*ms)
        
        self.set_dataset('TTL_counts',(count_tot),broadcast=True)
        



