'''  
 - trying to make this one simular to the run_pmt_continuously on Haeffner lba github


    '''

import sys
import os
#import datetime import datetime
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
from artiq import *
from artiq.language import *
from artiq.language.core import TerminationRequested
import numpy as np

#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')


#def pc(self,counts): 
#    print(counts)

# Class which defines the pmt counting experiment
class counts_continuously(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         # set arguments that can be varied on the dashboard 
         
         self.setattr_argument('detection_time',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used
         self.dataset_length = {}
#    def prepare(self):
	# this function runs before the experiment, set dataset variables here
#        self.time_interval=np.linspace(0,(self.step_size)*(self.time_count-1)/1.0e3,self.time_count)
#        self.set_dataset('times',(self.time_interval),broadcast=True)
    def run(self):
        self.core.reset()
        self.set_dataset("counts",[],broadcast=True)
        self.set_dataset("collection_duration",[self.detection_time])
        self.set_dataset("clear_pmt_plot",[False],broadcast=True)
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            self.run_pulse_counter()
   
    # run_pmt, this is directly counting pulses in FPGA and decorated with kernel so that artiq is listening/waiting for a pulse for 100ms        
    @kernel
    def run_pulse_counter(self):
        self.core.break_realtime()
        # runs this function while not paused (so continusouly)
        while not self.scheduler.check_pause():
            self.core.break_realtime()
            
            #counts the rising edges within a certain detection time
            t_count=self.ttl3.gate_rising(self.detection_time*ms) # reads from the channel
            count =self.ttl3.count(t_count)
            self.append("counts",count)
        
        #self.set_dataset('TTL_counts',(counts),broadcast=True)
    @rpc(flags={"async"})
    def append(self, dataset_name, data_to_append):
        if not dataset_name in self.dataset_length.keys():
            self.dataset_length[dataset_name] = 0

        if self.dataset_length[dataset_name] % 1000 == 0:
            self.set_dataset(dataset_name, [], broadcast=True)

        self.append_to_dataset(dataset_name, data_to_append)
        self.dataset_length[dataset_name] += 1
    
    @rpc(flags={"async"}) 
    def pc(self,count): 
        print(count)           



