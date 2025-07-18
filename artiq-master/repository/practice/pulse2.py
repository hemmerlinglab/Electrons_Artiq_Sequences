from artiq.experiment import *

def print_underflow():
    print("RTIO underflow occured")

class Pulse2(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("ttl4")

    @kernel
    def run(self):
        self.core.reset()
        try:
            for i in range(1000000):
                self.ttl4.pulse(1*ns)
                delay(1*ns)
        except RTIOUnderflow:
            print_underflow()
