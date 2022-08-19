'''Zijue Luo: Trying to build a code to let zotino to send a 10ns pulse
Conclusion: zotino is not capable to generate 10ns pulses since it takes
too long for the voltage to rise (~10us)'''
from artiq.experiment import *
import numpy as np


class Zotino(EnvExperiment):

    def build(self):
        
        self.setattr_device('core')
        self.setattr_device('zotino0')
#        self.setattr_device('scheduler')

#        self.setattr_argument('voltage', NumberValue(default=0.1,unit='V',max=1.0,min=0.0,scale=1,ndecimals=1,step=0.1))
    
#    @kernel
#    def initialize_zotino(self):

        
#    @kernel
#    def send_pulse(self, voltage):

    @kernel
    def run(self):
        
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us) # this is important to avoid RTIO underflows
        self.zotino0.write_gain_mu(0, 65000)
        
        # Using machine unit is required to prevent RTIO Underflows
        while(True):
            self.zotino0.write_dac_mu(0, 50000)
            self.zotino0.load()
            delay(10*us)
            self.zotino0.write_dac_mu(0, 1)
            self.zotino0.load()
            delay(20*us)


#        self.initialize_zotino()
#        self.send_pulse(self.voltage)
        
