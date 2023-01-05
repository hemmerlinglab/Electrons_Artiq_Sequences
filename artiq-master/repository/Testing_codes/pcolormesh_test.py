'''Zijue Luo: Trying to build a 2D histogram applet'''
from artiq.experiment import *
import numpy as np

class pcolormesh_test(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        
        self.setattr_argument('no_of_bins', NumberValue(default=30,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('range_of_center', NumberValue(default=1,unit='',scale=1,ndecimals=2,step=0.01))
        self.setattr_argument('no_of_steps', NumberValue(default=21,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('sample_size', NumberValue(default=200,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('std', NumberValue(default=1,unit='',scale=1,ndecimals=2,step=0.01))

#    def prepare(self):

#        self.set_dataset('xvalues', )

    def get_datas(self):
        
        bins = np.linspace(-5 * self.range_of_center, 5 * self.range_of_center, self.no_of_bins)
        my_histograms = np.zeros((self.no_of_steps, len(bins)-1))
        centers = np.linspace(-self.range_of_center, self.range_of_center, self.no_of_steps)

        samples = np.zeros((self.no_of_steps, self.sample_size))
        for i in range(self.no_of_steps):
            samples[i] = np.random.normal(centers[i], self.std, self.sample_size)
            my_histograms[i], my_bins = np.histogram(samples[i], bins=bins)

        return my_bins, np.array(range(self.no_of_steps)), my_histograms

#    @kernel
    def run(self):
        y, x, val = self.get_datas()

        self.set_dataset('xval', x, broadcast=True)
        self.set_dataset('yval', y, broadcast=True)
        self.set_dataset('values', val, broadcast=True)
