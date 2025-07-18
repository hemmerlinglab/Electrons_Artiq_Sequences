from artiq.experiment import *
class Pulse4(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("ttl4")
        self.setattr_device("ttl12")
    @kernel
    def run(self):
        self.core.reset()
        for i in range(10000000):
            with parallel:
                with sequential:
                    self.ttl4.pulse(2*us)
                    delay(1*us)
                    self.ttl4.pulse(1*us)
                with sequential:
                    self.ttl12.pulse(3*us)
                    delay(3*us)
            delay(4*us)
