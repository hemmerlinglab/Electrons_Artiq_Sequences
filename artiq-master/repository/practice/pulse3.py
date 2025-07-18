from artiq.experiment import *

class Pulse3(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("ttl4")
        self.setattr_device("ttl12")

    @kernel
    def run(self):
        self.core.reset()
        for i in range(10000000):
            with parallel:
                self.ttl4.pulse(2*us)
                self.ttl12.pulse(4*us)
            delay(4*us)
