''' Differences from V3: 
 - no more hard coded detection time, dont forget to recompute all arguments'''

# import sys
# import os
# import datetime
# import select
from artiq.experiment import *
# from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np



#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')

# Class which defines the pmt counting experiment
class DAC_Test(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         self.setattr_device('ttl6') # where pulses are being sent in by ttl
         self.setattr_argument('time_count', NumberValue(default=40,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('no_of_averages', NumberValue(default=10,unit='number of averages',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used
         
         self.setattr_device('zotino0') # scheduler used
         
         self.setattr_argument('offset_voltage', NumberValue(default=1,unit='V',min=0,max=5,scale=1,ndecimals=1,step=1))
         
         #self.my_voltage = self.zotino0.voltage_to_mu(0.025)




    def prepare(self):
        self.set_dataset('count_tot',[0.0]*self.time_count,broadcast=True)


    @kernel
    def my_setup(self, voltage):
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us) # this is important to avoid RTIO underflows

        ##self.zotino0.write_gain_mu(0, 65000)

        #self.zotino0.write_offset_mu(0, self.offset_voltage)
        #
        #self.zotino0.write_dac_mu(0, self.my_voltage) 


        #self.zotino0.load()
        
        self.zotino0.write_gain_mu(0, 65000)
        
        #self.zotino0.write_offset_mu(0, 1500)
        #self.zotino0.load()
        
        #self.zotino0.write_dac_mu(0, 0x1500)#self.offset_voltage_mu)
        self.zotino0.write_dac(0, voltage)
        
        self.zotino0.load()

        #self.zotino0.set_leds(8)


    @kernel
    def counting(self):


        self.core.reset()
        self.core.break_realtime()
        
    
        #self.zotino0.init()
        #delay(200*us)


        #self.zotino0.write_dac_mu(0, 1500)
        #
        #self.zotino0.write_dac(0, 1.2)
        #self.zotino0.load()
    
        #self.zotino0.set_leds(4)

        # read the counts and store into a dataset for live updating
        
        ##for j in range(5):
        #if True:

        #    with parallel:

        #        with sequential:
        #            
        #            # trigger of function generator
        #            self.ttl6.pulse(50*us)

        #                
        #        with sequential:
        #            
        #            #for j in range(2):
        #            #register rising edges for detection time
        #    
        #            self.counts = self.ttl3.count(self.ttl3.gate_rising(self.detection_time*us))
        #                
        #            #delay(1*self.detection_time*us)
               

    def run(self):

        self.my_setup(self.offset_voltage)
        self.counts = 0


        volt_arr = np.linspace(0, 1, 10)

        for k in range(len(volt_arr)):
            self.scheduler.pause() # allows for "terminate instances" functionality
        
            self.my_setup(volt_arr[k])
   
            self.counting()
            #val = AD53xx.voltage_to_mu(self, my_vals[k])
            #self.zotino0.write_dac_mu(0, 1)
          
            time.sleep(1)


        self.my_setup(0.0)


