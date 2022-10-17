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
class gate_counting_template(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         self.setattr_device('ttl6') # where pulses are being sent in by ttl
         self.setattr_argument('time_count', NumberValue(default=40,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('no_of_averages', NumberValue(default=10,unit='number of averages',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=1,unit='us',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.set_dataset('count_tot',[0.0]*self.time_count,broadcast=True)


    @kernel
    def counting(self):
        #new_data = [0.0]*self.time_count

        self.core.break_realtime()
        # read the counts and store into a dataset for live updating
        
        #for j in range(5):
        #if True:

        data0 = [0] * self.no_of_averages

        with parallel:

            with sequential:
                
                # trigger of function generator
                for j in range(self.no_of_averages):
                    self.ttl6.pulse(50*ns)

                    delay(1*self.detection_time*us)

                    delay(10*us)
                    
            with sequential:
                
                for j in range(self.no_of_averages):
                    #register rising edges for detection time
                    
                    delay(50*ns)

                    ev = self.ttl3.gate_rising(self.detection_time*us)
             
                    data0[j] = self.ttl3.count(ev)
                    
                    #self.counts = self.ttl3.count(self.ttl3.gate_rising(self.detection_time*us))
                    
                    #delay(1*self.detection_time*us)
                    
                    delay(10*us)
       

        #for j in range(self.no_of_averages):
        #     data0[j] = self.ttl3.count(data0[j])
        #     #data0[j] = self.ttl3.fetch_timestamp_count()


        self.set_dataset('counts', (data0), broadcast = True)


            
    #@rpc(flags={'async'})
    #def pc(self,new_data):

    #    self.set_dataset('count_tot',new_data, broadcast=True)



    def run(self):
        self.core.reset()


        counter = 0

        self.counts = 0
        self.avg_counts = 0

        self.ev = 10 * [0]
        
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            
            self.avg_counts = 0
            for n in range(self.no_of_averages):
                self.counting()

                cts = self.get_dataset('counts')

                print(cts)

                self.avg_counts += self.counts
                    
            self.avg_counts = 1.0 * self.avg_counts / self.no_of_averages

            self.mutate_dataset('count_tot', counter % self.time_count, (1.0 * self.avg_counts)/(self.detection_time*us))
   
            #counter = counter % self.time_count

            #print(counter)
            #print(counter % self.time_count)
            counter += 1

