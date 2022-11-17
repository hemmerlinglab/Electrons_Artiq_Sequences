from artiq.experiment import *

class Pulse(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('ttl11')

    @kernel
    def run(self):
        
        self.core.reset()
        while True:
            self.ttl11.pulse(1*us)
            delay(10*us)
