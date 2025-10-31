
from artiq.experiment import *                  #imports everything from artiq experiment library

#This code demonstrates how to use a TTL pulse(channel3) to trigger another event.
#In this code the event being triggered is another ttl pulse 
#however the same principle can be used to trigger an experimental sequence.

#pulses occur 5.158us appart with about 1ns jitter

class TTL_Input_As_Trigger(EnvExperiment):
    """TTL Input Edge as Trigger Only"""
    def build(self): #Adds the device drivers as attributes and adds the keys to the kernel invarients     

        self.setattr_device("core")             #sets drivers of core device as attributes
        self.setattr_device("ttl3")             #sets drivers of TTL3 as attributes
        self.setattr_device("ttl6")             #sets drivers of TTL6 as attributes
        self.setattr_device('scheduler') # scheduler used
                               
       
    @kernel #this code runs on the FPGA
    def Trigger(self):
        self.core.reset()                       #resets core device 

        self.ttl3.input()                       #sets TTL3 as an input
        self.ttl6.output()                      #sets TTL6 as an output
        self.ttl6.off()
        delay(1*ms)                             #1us delay, necessary for using trigger, no error given if removed
        
        t_end = self.ttl3.gate_rising(10*ms)    #opens gate for rising edges to be detected on TTL3 for 10ms
                                                #sets variable t_end as time(in MUs) at which detection stops
                                                
        t_edge = self.ttl3.timestamp_mu(t_end)  #sets variable t_edge as time(in MUs) at which first edge is detected
                                                #if no edge is detected, sets t_edge to -1

        if t_edge > 0:                          #runs if an edge has been detected
            at_mu(t_edge)                       #set time cursor to position of edge
            delay(5*us)                         #5us delay, to prevent underflow
            self.ttl6.pulse(5*ms)               #outputs 5ms pulse on TTL6

        self.ttl3.count(t_end)                 #discard remaining edges and close gate
    
    def run(self):
        while True:
            self.scheduler.pause()             # allows for "terminate instances" functionality
            self.Trigger()

