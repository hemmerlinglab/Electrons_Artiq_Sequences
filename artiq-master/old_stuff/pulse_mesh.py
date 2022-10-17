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
class Pulse_Mesh_Counting(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         self.setattr_device('ttl9') # where pulses are being sent in by ttl
         self.setattr_device('zotino0') # where pulses are being sent in by ttl
         self.setattr_argument('time_count', NumberValue(default=200,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('no_of_averages', NumberValue(default=500,unit='number of averages',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used

         self.setattr_argument('mesh_voltage', NumberValue(default=150,unit='V',min=0,max=600,scale=1,ndecimals=1,step=1))

    def prepare(self):
        self.set_dataset('count_tot',[0.0]*self.time_count,broadcast=True)


    @kernel
    def counting(self):
        #new_data = [0.0]*self.time_count

        self.core.break_realtime()
        # read the counts and store into a dataset for live updating
        

        data0 = [0] * self.no_of_averages

        trigger_length = 50.0 * ns

        for j in range(self.no_of_averages):
            with parallel:
                with sequential:
                
                    delay(trigger_length)

                    # trigger of function generator
                    self.ttl9.pulse(trigger_length)

                    delay(1.0*self.detection_time*us)

                    delay(1*us)
                    
                with sequential:
                
                    #register rising edges for detection time
                    
                    delay(trigger_length)

                    ev = self.ttl3.gate_rising(self.detection_time*us)
             
                    data0[j] = self.ttl3.count(ev)
                    
                    delay(1.0*self.detection_time*us)
                    
                    delay(1*us)
                    
                    delay(trigger_length)
       


        self.set_dataset('counts', (data0), broadcast = True)




    def run(self):
        
        self.core.reset()
        
        #self.set_mesh_voltage( 1.0/200.0 * self.mesh_voltage )
        
        time.sleep(1)



        counter = 0

        self.counts = 0
        self.avg_counts = 0

        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            
            self.counting()

            cts = np.array(self.get_dataset('counts'))

            #print(cts)
            #self.avg_counts = 1.0 * np.mean(cts)/(1.0 * self.detection_time * us)
            self.avg_counts = np.mean(cts)

                    
            self.mutate_dataset('count_tot', counter % self.time_count, self.avg_counts)
   
            counter += 1




