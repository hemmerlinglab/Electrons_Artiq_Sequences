'''Zijue Luo: building a code that can output different voltages from the zotino in order 
to test the output of the D sub connector'''

from artiq.experiment import *
import numpy as np

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import adjust_set_volt

class zotino_channel_differentiation(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('zotino0')

    @kernel
    def set_electrode_voltages(self, channel_list, voltage_list):
        
        voltage = 0

        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)

        for k in range(len(channel_list)):
        #for k in [0,1]:

            self.zotino0.write_gain_mu(channel_list[k], 65000)
            self.zotino0.load()
            delay(200*us)
            self.zotino0.write_dac(channel_list[k], voltage_list[k])
            self.zotino0.load()
            delay(200*us)

        return

    def run(self):

        channels = np.arange(0, 28)
        voltages = 0.1 * channels
        for i in range(len(voltages)):
            voltages[i] = adjust_set_volt(i, voltages[i])
        print(channels)
        print(voltages)

        self.set_electrode_voltages(channels, voltages)
