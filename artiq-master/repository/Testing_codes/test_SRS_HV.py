from artiq.experiment import *
import numpy as np
import time

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import adjust_set_volt

class Test_SRS_HV(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('zotino0')

        self.setattr_argument('mode', EnumerationValue(['Auto','Manual'],default='Auto'))
        self.setattr_argument('channel', NumberValue(default=28,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('voltage', NumberValue(default=0,unit='V',scale=1,ndecimals=2,step=0.01))

    @kernel
    def set_voltage(self, channel, voltage):
        
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)

        self.zotino0.write_gain_mu(channel, 65000)
        self.zotino0.load()
        delay(200*us)
        self.zotino0.write_dac(channel, voltage)
        self.zotino0.load()
        delay(200*us)

        return

    def run(self):

        if self.mode == 'Manual':
            voltage = adjust_set_volt(self.channel, self.voltage)
            print('Adjusted voltage setpoint: ' + str(voltage))
            self.set_voltage(self.channel, voltage)

        else:
            time.sleep(5)
            voltages = np.linspace(-10, 9, 20)
            for v in voltages:
                va = adjust_set_volt(self.channel, v)
                print('Original: ' + str(v) + ', Adjusted: ' + str(va))
                self.set_voltage(self.channel, va)
                time.sleep(2)
