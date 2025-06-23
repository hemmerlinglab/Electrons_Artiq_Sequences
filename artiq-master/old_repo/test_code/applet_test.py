from artiq.experiment import *
import numpy as np

class Applet_test(EnvExperiment):

    def build(self):
        self.setattr_device('core')
        self.setattr_argument('max', NumberValue(default=100,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('refresh_time', NumberValue(default=0.2,unit='s',scale=1,ndecimals=1,step=0.1))

    def prepare(self):
        xs = np.linspace(0, 1, self.max)
        self.set_dataset('xaxis', xs, broadcast=True)
        self.set_dataset('values', [0] * self.max, broadcast=True)

    @kernel
    def run(self):
        for i in range(self.max):
            delay(self.refresh_time*s)
            self.mutate_dataset('values', i, i)
            i += 1
