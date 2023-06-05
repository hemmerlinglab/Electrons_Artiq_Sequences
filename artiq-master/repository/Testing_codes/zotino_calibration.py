from artiq.experiment import *
import numpy as np
from time import sleep

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import adjust_set_volt

class zotino_calibration(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('zotino0')

        self.setattr_argument('channel', NumberValue(default=0,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('mode', EnumerationValue(['Sampling', 'Testing', 'Reseting'], default='Reseting'))
        
    @kernel
    def zotino_out(self, channel, level):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(channel, 65000)
        self.zotino0.write_dac(channel, level)
        self.zotino0.load()

        return

    def run(self):

        self.core.reset()
        if self.mode == 'Sampling':
            volts = np.linspace(-10, 10, 21)
            volts[20] = 9.9
            sleep(10)
            for v in volts:
                print('setpoint:', v)
                self.zotino_out(self.channel, v)
                sleep(5)

        elif self.mode == 'Testing':
            volts = np.linspace(-10, 9, 20)
            sleep(10)
            for v in volts:
                #print('setpoint:', v)
                self.zotino_out(self.channel, adjust_set_volt(self.channel, v))
                sleep(2)

        elif self.mode == 'Reseting':
            for i in range(30):
                self.zotino_out(i, adjust_set_volt(i, 0))
