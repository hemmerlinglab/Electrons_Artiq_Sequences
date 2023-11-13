from artiq.experiment import *
import numpy as np

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *
from dc_electrodes import *

class Count_with_U2(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('ttl3')
        self.setattr_device('zotino0')

        self.setattr_argument('time_count', NumberValue(default=10,unit='s',scale=1,ndecimals=1,step=0.1))
        self.setattr_argument('mesh_voltage', NumberValue(default=150,unit='V',min=0,max=600,scale=1,ndecimals=1,step=1))
        self.setattr_argument('U2', NumberValue(default=0,unit='',min=0,max=0.69,scale=1,ndecimals=2,step=0.01))

    @kernel
    def set_mesh_voltage(self, voltage):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(31, 65000)
        self.zotino0.write_dac(31, 1.0/198.946 * (voltage + 14.6027))
        self.zotino0.load()

        return

    @kernel
    def set_electrode_voltages(self, channel_list, voltage_list):

        print('Function 2 called!')
        
        voltage = 0

        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
                
        for k in range(len(channel_list)):

            self.zotino0.write_gain_mu(channel_list[k], 65000)
            self.zotino0.load()
            delay(200*us)
            self.zotino0.write_dac(channel_list[k], voltage_list[k])
            self.zotino0.load()
            delay(200*us)

        return

    def prepare(self):
        
        # Compute the voltages of DC electrodes we want
        self.multipole_vector = {
                'Ex' : 0,
                'Ey' : 0,
                'Ez' : 0,
                'U1' : 0,
                'U2' : self.U2,
                'U3' : 0,
                'U4' : 0,
                'U5' : 0
            }
        print('Vector Defined!')
        (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
        print('Voltages Computed!')
        print('chans:', chans)
        print('voltages:', voltages)
        self.set_electrode_voltages(chans, voltages)
        print('Electrode voltages applied!')

        # Set mesh voltages
        self.set_mesh_voltage(self.mesh_voltage)
        print('Mesh voltage already set!')

    def analyze(self):
        print('Total Count:', self.ct)

    @kernel
    def run(self):

        self.core.reset()
        
        ev = self.ttl3.gate_rising(self.time_count*s)
        self.ct = self.ttl3.count(ev)
