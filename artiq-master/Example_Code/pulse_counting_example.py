import sys
import os
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np

def print_underflow():
    print('RTIO underflow occured')


class pulse_counting(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
    def run(self):
        self.core.reset()
        self.counting(100)
   
    @kernel
    def counting(self,detection_time):
        while True:
            self.core.break_realtime()
            # registers the number of rising edges within a detection time
            t_count = self.ttl3.gate_rising(detection_time*ms)
            # counts the registers stored in t_count, stores in pmt_count
            pmt_count = self.ttl3.count(t_count)
            self.pc(pmt_count)
    
    #breaks from artiq kernel, computer prints counts 
    @rpc(flags={"async"}) 
    def pc(self,counts): 
        print(counts)
