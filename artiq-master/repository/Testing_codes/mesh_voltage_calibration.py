'''Zijue Luo: Code for calibrating mesh voltages'''

from artiq.experiment import *
import numpy as np

#import sys
#sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
#from helper_functions import adjust_set_volt

class Mesh_Voltage_Calibration(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('zotino0')

        self.setattr_argument('mode', EnumerationValue(['Data Sampling', 'Test Performance'],default='Test Performance'))
        self.setattr_argument('trigger_level', NumberValue(default=0,unit='V',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('mesh_voltage', NumberValue(default=0,unit='V',scale=1,ndecimals=0,step=1))

    @kernel
    def send_trig_to_mesh(self, level):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(31, 65000)
        self.zotino0.write_dac(31, level)
        self.zotino0.load()

        return

    @kernel
    def set_mesh_voltage(self, voltage):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(31, 65000)
        self.zotino0.write_dac(31, 1.0/198.946 * (voltage + 14.6027))
        self.zotino0.load()

        return
        
    def analyze(self):
    
    	print('Done !')

    def run(self):
        
        self.core.reset()
        if self.mode == 'Data Sampling':
            self.send_trig_to_mesh(self.trigger_level)
        elif self.mode == 'Test Performance':
            self.set_mesh_voltage(self.mesh_voltage)
