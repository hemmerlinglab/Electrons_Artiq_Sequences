from artiq.experiment import *
import numpy as np

class Continuous_Counting(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('ttl3')
        self.setattr_device('scheduler')

        self.setattr_argument('detection_time', NumberValue(default=50,unit='ms',scale=1,ndecimals=1,step=0.1))
        self.setattr_argument('time_count', NumberValue(default=201,unit='',scale=1,ndecimals=0,step=1))

    def prepare(self):

        self.set_dataset('scan_result', [0.0] * self.time_count, broadcast=True)
        self.set_dataset('scan_x', [i for i in range(self.time_count)], broadcast=True)

        self.core.reset()

    @kernel
    def count(self):
        self.core.break_realtime()
        ev = self.ttl3.gate_rising(self.detection_time * ms)
        return self.ttl3.count(ev)

    def run(self):

        counter = 0

        while True:

            self.scheduler.pause()
            cts = self.count()
            self.mutate_dataset('scan_result', counter % self.time_count, cts)
            counter += 1
