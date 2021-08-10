# imports most commonly used features from ARTIQ language modules and from core device
from artiq.experiment import *

# python libraries examples (uncomment to have)
# import time 
# import numpy as np

class example(EnvExperiment):
    def build(self):
        self.setattr_device('core') #need the core for everything
        # examples of other devices you can use
        self.setattr_device('led')
        self.setattr_device('sampler0') # sampler device, specifiy which sampler
        self.setattr_device('ttl3') #ttl port 3 used
        self.setattr_device('scheduler') #scheduler for timing
        self.setattr_argument('Experiment_param',NumberValue(default=100,unit='units',scale=1,ndecimals=0,step=1))

    @kernel
    def run(self):
        self.core.reset() #always reset the core at the begining of run
        # some code


