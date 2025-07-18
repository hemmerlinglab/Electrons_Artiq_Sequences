from artiq.experiment import *
class Pulse5(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("ttl4")
        self.setattr_device("ttl12")
    @kernel
    def run(self):
        self.core.reset()
        with parallel:
            self.pulse_ttl4()
            self.pulse_ttl12()
    @kernel
    def pulse_ttl4(self):
        for i in range(1000000):
            self.ttl4.pulse(1*us)
            delay(1*us)
            self.ttl4.pulse(1*us)
            delay(1*us)
    @kernel
    def pulse_ttl12(self):
        for i in range(1000000):
            self.ttl12.pulse(3*us)
            delay(1*us)
            if i % 100 == 0:
                self.core.break_realtime()











