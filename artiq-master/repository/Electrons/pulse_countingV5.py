''' Differences from V4: 
 - continuosly append to list, if list is greater than 400, delete up to 400

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
class pulse_counting5(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         # set arguments that can be varied on the dashboard 
         
         self.setattr_argument('step_size',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1)) #time scale on the scope,how zoomed you are in time
    
         self.setattr_argument('time_count', NumberValue(default=400,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used
         self.dataset_length = {}
    def prepare(self):
	# this function runs before the experiment, set dataset variables here
        self.time_interval=np.linspace(0,(self.step_size)*(self.time_count-1)/1.0e3,self.time_count)
        self.set_dataset('times',(self.time_interval),broadcast=True)
        self.set_dataset('count_tot',[0]*self.time_count,broadcast=True)
    def run(self):
        self.core.reset()
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            self.counting()
   
    #  directly counting pulses in FPGA and decorated with kernel -> artiq is listening/waiting for a pulse for a certain detection time        
    @kernel
    def counting(self):
        self.core.break_realtime()

        for j in range(self.time_count):
            #register rising edges for detection time
            t_count= self.ttl3.gate_rising(self.detection_time*ms) # reads from the channel
            count =self.ttl3.count(t_count)
            # mutate dataset at index j with the value of count
            self.mutate_dataset('count_tot',j,count)
            # delay for as long your listening for, translates between machine time and actual time
            delay(self.detection_time*ms)
            #self.append("count_tot", count)
        
    # not used but thinking of using this    
    @rpc(flags={"async"})
    def append(self, dataset_name, data_to_append):
        if not dataset_name in self.dataset_length.keys():
            self.dataset_length[dataset_name] = 0

        if self.dataset_length[dataset_name] % 1000 == 0:
            self.set_dataset(dataset_name, [], broadcast=True)

        self.append_to_dataset(dataset_name, data_to_append)
        self.dataset_length[dataset_name] += 1



