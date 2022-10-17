import sys
import os
#import datetime import datetime
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np
#import matplotlib.pyplot as plt

#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')


# Class which defines the pmt counting experiment --> shows up in the GUI as this name
class basic_live_scope_view2(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('sampler0') # where voltages being read in
         self.setattr_argument('step_size',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1)) #time scale on the scope,how zoomed you are in time
         self.setattr_argument('scope_count', NumberValue(default=400,unit='reads per shot',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1)) #this makes detection time an attribute to change on GUI 
         self.setattr_device('scheduler') # scheduler used
    
    def prepare(self):
        #function run before the experiment 
        
        #each sampler takes 9us in addition to whatever the time delay is
        # scope count -1 for endpoint considerations
        # division converts it to ms
        self.time_interval = np.linspace(0,(self.step_size+9)*(self.scope_count-1)/1.0e3,self.scope_count)

        # turn np array into a dataset, time dataset for scope
        self.set_dataset('times', (self.time_interval),broadcast=True)
    
    def run(self):
        self.core.reset()
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            self.run_pmt()
    
    # run_pmt, this is directly counting pulses in FPGA and decorated with kernel so that artiq is listening/waiting for a pulse for 100ms        
    @kernel
    def run_pmt(self):
        #while True:
        self.core.break_realtime()
        self.sampler0.init() #initializes sampler

        # sets the gain for each sampler
        for i in range(8):
            self.sampler0.set_gain_mu(i,0)

        delay(260*us)

        # list for redefines 0's with a value read in from sampler
        # data0 is from a single scope count
        data0 = [0]*self.scope_count

        # add to smp data by continuously overriding, list of 8 points of all zeros
        smp = [0]*8

        # smp has been overriden
        for j in range(self.scope_count):
            #acquire set of data (data)
            self.sampler0.sample_mu(smp) # reads in machine units from 8 channels
            # save the value of smp
            data0[j] = smp[0]
            delay(self.step_size*us)

        self.set_dataset('volts',(data0),broadcast=True)


