'''Zijue Luo: Count events in the same configuration for a long period of time,
used to scan over threshold.'''

from artiq.experiment import *
import numpy as np

class Long_Term_Count(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('ttl3')

        self.setattr_argument('time_count', NumberValue(default=10,unit='s',scale=1,ndecimals=1,step=0.1))
        self.ct = 0

    def analyze(self):
        print('Total Count:', self.ct)

    @kernel
    def run(self):

        self.core.reset()
        
        ev = self.ttl3.gate_rising(self.time_count*s)
        self.ct = self.ttl3.count(ev)
