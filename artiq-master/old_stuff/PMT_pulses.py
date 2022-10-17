#PMT testing code #1:
    #To-do:-check the pulse width

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


# Class which defines the pmt counting experiment
class DAQ(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         self.setattr_device('ttl12') # where pulses are being sent in by ttl
         
         self.setattr_device('ttl14') # where pulses are being sent in by ttl
         
    def run(self):
        self.core.reset()
        self.run_pmt(20)
   
    # run_pmt, this is directly counting pulses in FPGA and decorated with kernel so that artiq is listening/waiting for a pulse for 100ms        
    @kernel
    def run_pmt(self,detection_time):
        while True:
            self.core.break_realtime()


            self.ttl12.pulse(10*us) # experimental start
            delay(10*ns)
            
            with parallel:
                with sequential:

                    delay(20*ns)
                    
                    for k in range(10):
                        self.ttl14.pulse(10*ns) # experimental start
                        delay(11*ns)

                with sequential:
                    t_count = self.ttl3.gate_rising(detection_time*ms)
                    pmt_count = self.ttl3.count(t_count)
                    self.pc(pmt_count)

    #prints the counts, decorated with rpc because this is something computer does, do not want to wait for artiq to count before going to next line, want to do it simultaneously  
    @rpc(flags={"async"})
    def pc(self,counts):
        print(counts)