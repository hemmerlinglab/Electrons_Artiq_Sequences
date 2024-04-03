from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

from dc_electrodes import *

class DacTest(EnvExperiment):
    
    def build(self):
        
        self.setattr_device('core')
        self.setattr_device('scheduler')
        self.setattr_device('zotino0')
        self.setattr_device('ttl16')

   
        return

    @kernel
    def test(self):
        
        voltage = 0

        self.core.reset()
        self.core.break_realtime()

        self.zotino0.init()        
        delay(200*us)

        no_of_chans = 40

        for k in range(no_of_chans):

            self.zotino0.write_gain_mu(k, 65000)
            self.zotino0.load()            
            delay(50*us)

        self.ttl16.pulse(1*ms)
        
        for k in range(no_of_chans):

            self.zotino0.write_gain_mu(k, 65000)
            self.zotino0.load()            
            delay(50*us)

            for n in range(k+1):

                self.zotino0.write_dac(k, 9.0)
            
                self.zotino0.load()
                delay(50*us)

                delay(100*us)

                self.zotino0.write_dac(k, 0.0)
            
                self.zotino0.load()
                delay(50*us)

        #self.ttl16.pulse(2*ms)

        return

    def prepare(self):

        self.core.reset() # Reset the core

    def analyze(self):
        
        return

    def run(self):

        while True:
            self.scheduler.pause()
            self.test()



