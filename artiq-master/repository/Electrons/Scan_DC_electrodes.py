from artiq.experiment import *
import numpy as np

import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

class Scan_DC_Electrodes(EnvExperiment):

    def build(self):

        self.config_dict = []
        self.elec_dict = {'tl1': 0, 'tl2': 1, 'tl3': 2, 'tl4': 3, 'tl5': 4,
                          'tr1': 9, 'tr2': 8, 'tr3': 7, 'tr4': 6, 'tr5': 5,
                          'bl1': 12, 'bl2': 13, 'bl3': 14, 'bl4': 15, 'bl5': 16,
                          'br1': 21, 'br2': 20, 'br3': 19, 'br4': 18, 'br5': 17}

        self.setattr_device('core')
        self.setattr_device('ttl3')
        self.setattr_device('zotino0')

        self.setattr_argument('time_count', NumberValue(default=10,unit='s',scale=1,ndecimals=1,step=0.1))
        self.setattr_argument('mesh_voltage', NumberValue(default=150,unit='V',min=0,max=600,scale=1,ndecimals=1,step=1))
        self.setattr_argument('Zotino_channel', NumberValue(default=-1,min=-1,max=21,scale=1,ndecimals=0,step=1))
        self.setattr_argument('electrode', EnumerationValue(list(self.elec_dict.keys()),default='tl1'))     
        self.setattr_argument('minimum', NumberValue(default=-5,unit='V',min=-10,max=10,scale=1,ndecimals=1,step=0.1))
        self.setattr_argument('maximum', NumberValue(default=5,unit='V',min=-10,max=10,scale=1,ndecimals=1,step=0.1))
        self.setattr_argument('steps', NumberValue(default=21,unit='',scale=1,ndecimals=0,step=1))

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

        # Setting mute mode
        if self.Zotino_channel < 0: self.mute = False
        else: self.mute = True

        # Calculating scan values
        self.set_dataset('scan_result', [0.0] * self.steps, broadcast=True)
        self.scan_values = self.minimum + np.arange(0, self.steps) * (self.maximum - self.minimum) / (self.steps-1)
        self.set_dataset('scan_x', self.scan_values, broadcast=True)

        # Defining data need to save
        self.config_dict.append({'par': 'sequence_file', 'val': os.path.abspath(__file__), 'cmt': 'Filename of the main sequence file'})
        get_basefilename(self)

        self.data_to_save = [{'var': 'scan_x', 'name': 'scan_x'},
                             {'var': 'scan_result', 'name': 'counts'}]

        # Preparation for the experiment
        self.core.reset()
        self.set_mesh_voltage(0.0)

        chans = [0, 1, 2, 3, 4, 9, 8, 7, 6, 5, 12, 13, 14, 15, 16, 21, 20, 19, 18, 17]
        voltages = [0] * len(chans)
        self.set_electrode_voltages(chans, voltages)

        if not self.mute:
            print('Setting all electrodes to 0V ...')
            print('chans:', chans)
            print('voltages:', voltages, '\n')
            print('Sleeping for 1 seconds ...')

        time.sleep(0.1)

    def analyze(self):

        # Post experiment settings
        self.set_mesh_voltage(0.0)
        chans = [0, 1, 2, 3, 4, 9, 8, 7, 6, 5, 12, 13, 14, 15, 16, 21, 20, 19, 18, 17]
        voltages = [0] * len(chans)
        self.set_electrode_voltages(chans, voltages)

        if not self.mute:
            print('Setting mesh voltage to 0V ...')
            print('Setting all electrodes to 0V ...')
            print('chans:', chans)
            print('voltages:', voltages, '\n')
            
        print('End of scan.')

        # Saving data
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

        if self.Zotino_channel < 0:
            chan = [self.elec_dict[self.electrode]]
            electrode = self.electrode
        else:
            chan = [self.Zotino_channel]
            electrode = [key for key, value in self.elec_dict.items() if value == self.Zotino_channel][0]

        for k in range(self.steps):

            voltage = [self.scan_values[k]]

            if not self.mute:
                print('setting electrode ' + electrode + ' (Zotino channel ' + str(chan[0]) + ') to ' + str(voltage[0]) + 'V.')
                
            self.set_electrode_voltages(chan, voltage)
            time.sleep(0.05)

            self.count(k)

