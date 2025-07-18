from artiq.experiment import *

class Save1(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("ttl4")

    @kernel
    def run(self):
        self.core.reset()
        
        delay(100*us)
        for i in range(5):
            self.ttl4.pulse(0.1 * ms)
            delay(0.1 * ms)
