'''Trigger TTL from ARTIQ upon another TTL input'''

from artiq.experiment import *                  #imports everything from artiq experiment library
import numpy as np
#This code demonstrates how to use a TTL pulse(channel0) to trigger another event.
#In this code the event being triggered is another ttl pulse 
#however the same principle can be used to trigger an experimental sequence.

#pulses occur 5.158us appart with about 1ns jitter

def print_underflow():
    print('RTIO underflow occured')

class TTL_Input_As_Trigger2(EnvExperiment):
    def build(self): #Adds the device drivers as attributes and adds the keys to the kernel invarients     

        self.setattr_device("core")             #sets drivers of core device as attributes
        self.setattr_device("ttl0")             #sets drivers of TTL0 as attributes
        self.setattr_device("ttl6")             #sets drivers of TTL6 as attributes
        self.setattr_argument('time_count', NumberValue(default=400,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
        self.setattr_argument('detection_time',NumberValue(default=100,unit='ms',scale=1,ndecimals=0,step=1))
        self.setattr_device('scheduler') # scheduler used
    
    def prepare(self):
        self.set_dataset('count_tot',[0]*self.time_count,broadcast=True)

        self.core.reset()                       #resets core device
        
    def run(self):                              
        while True:
            self.scheduler.pause() # allows for "terminate instances" functionality
            self.trigger_counting()

    @kernel
    def trigger_counting(self):
        self.core.reset()
        self.core.break_realtime()
        
        delay(5*us)                             #1us delay, necessary for using trigger, no error given if removed
        
        t_end = self.ttl0.gate_rising(self.detection_time*ms)    #opens gate for rising edges to be detected on TTL0 for 10ms
                                                #sets variable t_end as time(in MUs) at which detection stops
                                                
        t_edge = self.ttl0.timestamp_mu(t_end)  #sets variable t_edge as time(in MUs) at which first edge is detected
                                                #if no edge is detected, sets t_edge to -1

        if t_edge > 0:                          #runs if an edge has been detected
            at_mu(t_edge)                       #set time cursor to position of edge
            delay(10*us)                         #5us delay, to prevent underflow
            self.ttl6.pulse(5*ms)               #outputs 5ms pulse on TTL6

        self.ttl0.count(t_end)                  #discard remaining edges and close gate
        # read the counts and store into a dataset for live updating
        for j in range(self.time_count):            #register rising edges for detection time
            t_count= self.ttl0.gate_rising(self.detection_time*ms) # reads from the channel
            count =self.ttl0.count(t_count)
            # mutate dataset at index j with the value of counts/second
            self.mutate_dataset('count_tot',j,(count)/(self.detection_time*ms))
            # delay for as long your listening for, translates between machine time and actual time
            delay(self.detection_time*ms)

   

