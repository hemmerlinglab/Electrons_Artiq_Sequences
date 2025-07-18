from artiq.experiment import *

class Pulse6(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("core_dma")
        self.setattr_device("ttl4")
    @kernel
    def record(self):
        with self.core_dma.record("pulses"):
            for i in range(5):
                self.ttl4.pulse(1*us)
                delay(1*us)
    @kernel
    def run(self):
        self.core.reset()
        self.record()
        
        pulses_handle = self.core_dma.get_handle("pulses")
        self.core.break_realtime()
       # for i in range (10):
        self.core_dma.playback_handle(pulses_handle)
            
