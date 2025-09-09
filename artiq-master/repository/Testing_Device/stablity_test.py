from artiq.experiment import *
from artiq.coredevice.ad53xx import AD53xx
import numpy as np

class Stability_test(EnvExperiment):

    def build(self):

        self.config_dict = []

        self.setattr_device('core')
        self.setattr_device('ttl3')

        self.setattr_argument('time_count', NumberValue(default=10,unit='s',scale=1,ndecimals=1,step=0.1))

    def prepare(self):

        self.set_dataset('scan_x', [0], broadcast=True)
        self.set_dataset('scan_result', [0.0], broadcast=True)

        self.core.reset()

    @kernel
    def run(self):

        self.core.break_realtime()

        ev = self.ttl3.gate_rising(self.time_count*s)
        ct = self.ttl3.count(ev)
        self.mutate_dataset('scan_result', 0, ct)

        k = 1
        while True:

            self.core.break_realtime()

            ev = self.ttl3.gate_rising(self.time_count*s)
            ct = self.ttl3.count(ev)
            self.append_to_dataset('scan_x', k)
            self.append_to_dataset('scan_result', ct)
            k += 1
