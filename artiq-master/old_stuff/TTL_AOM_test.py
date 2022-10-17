'''Zijue Luo: Trying to build a program to send a 10ns pulse by TTL,
in order to tune the AOM'''
from artiq.experiment import *
import numpy as np

class TTL_AOM_test(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('ttl9')

    @kernel
    def run(self):

        self.core.reset()
        self.core.break_realtime()

        while True:
            self.ttl9.pulse(10*ns)
            delay(1*us)
