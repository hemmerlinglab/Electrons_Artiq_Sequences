'''Zijue Luo: np.histogram misteriously does not work in artiq, trying to figure out why
Conclusion: np.histogram should works'''

from artiq.experiment import *
import numpy as np

class test(EnvExperiment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('scheduler')
        self.set_dataset('a', [], broadcast=True)

    @kernel
    def run(self):
        self.set_dataset('b', [0], broadcast=True)
