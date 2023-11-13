from artiq.experiment import *
import numpy as np

import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *
from dc_electrodes import *

class Scan_Multipoles(EnvExperiment):

    def build(self):

        self.config_dict = []

        self.setattr_device('core')
        self.setattr_device('ttl3')
        self.setattr_device('zotino0')

        self.setattr_argument('time_count', NumberValue(default=10,unit='s',scale=1,ndecimals=1,step=0.1))
        self.setattr_argument('mesh_voltage', NumberValue(default=150,unit='V',min=0,max=600,scale=1,ndecimals=1,step=1))
        self.setattr_argument('min_U2', NumberValue(default=0,unit='',min=0,max=0.69,scale=1,ndecimals=2,step=0.01))
        self.setattr_argument('max_U2', NumberValue(default=0.69,unit='',min=0,max=0.69,scale=1,ndecimals=2,step=0.01))
        self.setattr_argument('steps', NumberValue(default=70,unit='',scale=1,ndecimals=0,step=1))

        self.electrodes = Electrodes()

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

        self.set_dataset('scan_result', [0.0] * self.steps, broadcast=True)
        self.scan_values = self.min_U2 + np.arange(0, self.steps) * (self.max_U2 - self.min_U2) / (self.steps-1)
        self.set_dataset('scan_x', self.scan_values, broadcast=True)

        self.config_dict.append({'par': 'sequence_file', 'val': os.path.abspath(__file__), 'cmt': 'Filename of the main sequence file'})
        get_basefilename(self)

        self.data_to_save = [{'var': 'scan_x', 'name': 'scan_x'},
                             {'var': 'scan_result', 'name': 'counts'}]

        self.core.reset()
        self.set_mesh_voltage(0.0)
        print('Sleeping for 1 seconds ...')
        time.sleep(1)

    def analyze(self):

        print('Setting mesh voltage to 0V ...')
        self.set_mesh_voltage(0.0)

        print('Setting U2 to 0')
        multipole_vector = {
                'Ex' : 0,
                'Ey' : 0,
                'Ez' : 0,
                'U1' : 0,
                'U2' : 0,
                'U3' : 0,
                'U4' : 0,
                'U5' : 0
            }
        (chans, voltages) = self.electrodes.getVoltageMatrix(multipole_vector)
        print('chans:', chans)
        print('voltages:', voltages, '\n')
        self.set_electrode_voltages(chans, voltages)

        print('End of scan.')

        print('saving data ...')
        save_all_data(self)
        self.config_dict.append({'par': 'Status', 'val': True, 'cmt': 'Run finished.'})
        save_config(self.basefilename, self.config_dict)
        add_scan_to_list(self)
        print('Scan ' + self.basefilename + ' finished, file saved.')

    @kernel
    def count(self, k):

        self.core.break_realtime()
        
        ev = self.ttl3.gate_rising(self.time_count*s)
        ct = self.ttl3.count(ev)
        self.mutate_dataset('scan_result', k, ct)

    def run(self):

        for k in range(self.steps):

            multipole_vector = {
                    'Ex' : 0,
                    'Ey' : 0,
                    'Ez' : 0,
                    'U1' : 0,
                    'U2' : self.scan_values[k],
                    'U3' : 0,
                    'U4' : 0,
                    'U5' : 0
                }
            print('Setting U2 to ' + str(self.scan_values[k]))
            (chans, voltages) = self.electrodes.getVoltageMatrix(multipole_vector)
            print('chans:', chans)
            print('voltages:', voltages, '\n')
            self.set_electrode_voltages(chans, voltages)
            
            self.count(k)


