from artiq.experiment import *
import numpy as np

class Tickle_test(EnvExperiment):
    
    def build(self):

        self.setattr_device('core')
        self.setattr_device('ttl11')

    @kernel
    def run(self):

        self.core.reset()
        while True:
            self.core.break_realtime()
            self.ttl11.pulse(10*us)
            delay(20*us)
