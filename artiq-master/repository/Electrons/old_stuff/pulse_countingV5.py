''' Differences from V3: 
 - no more hard coded detection time, dont forget to recompute all arguments'''

# import sys
# import os
# import datetime
# import select
from artiq.experiment import *
# from artiq.coredevice.ad9910 import AD9910
# from artiq.coredevice.ad53xx import AD53xx
# import time
import numpy as np

#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')

# Class which defines the pmt counting experiment
class pulse_counting5(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         self.setattr_argument('time_count', NumberValue(default=400,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.set_dataset('count_tot',[0.0]*self.time_count,broadcast=True)

    def run(self):
        self.core.reset()

        print('Starting counting sequence ...')
        # while loop continuously repopulates the graph
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            self.counting()
   

    @kernel
    def counting(self):
        #new_data = [0.0]*self.time_count

        self.core.break_realtime()
        # read the counts and store into a dataset for live updating
        for j in range(self.time_count):
            #register rising edges for detection time
            
            counts = self.ttl3.count(self.ttl3.gate_rising(self.detection_time*us))

            # change to count rate
            #new_data[j] = counts / (self.detection_time * us)
            
            
            
            # mutate dataset at index j with the value of counts/second
            delay(1*self.detection_time*us)
       
            self.mutate_dataset('count_tot',j,(counts)/(self.detection_time*us))
            

            #self.pc(new_data)

        # delay for as long your listening for, translates between machine time and actual time
        
            
    @rpc(flags={'async'})
    def pc(self,new_data):

        self.set_dataset('count_tot',new_data, broadcast=True)
        # self.mutate_dataset('count_tot',j,(count)/(self.detection_time*us))

