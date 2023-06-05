'''Zijue Luo: Sometimes there are chaos on the threshold detector (or threshold voltage)
that will make the counts to jump to sky suddenly, this code aims to auto correct the
data when that happens'''

from artiq.experiment import *
from artiq.coredevice.ad53xx import AD53xx
import numpy as np

import time
import os
import sys
sys.path.append('/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions')
from helper_functions import *

class Scan_Mesh_Correction(EnvExperiment):

    def build(self):

        self.config_dict = []

        self.setattr_device('core')
        self.setattr_device('ttl3')
        self.setattr_device('zotino0')
        self.setattr_device('scheduler')

        self.setattr_argument('time_count', NumberValue(default=10,unit='s',scale=1,ndecimals=1,step=0.1))
        self.setattr_argument('min_volt', NumberValue(default=0,unit='V',scale=1,ndecimals=1,step=1))
        self.setattr_argument('max_volt', NumberValue(default=200,unit='V',scale=1,ndecimals=1,step=1))
        self.setattr_argument('steps', NumberValue(default=11,unit='',scale=1,ndecimals=0,step=1))

    def prepare(self):

        self.set_dataset('scan_result', [0.0] * self.steps, broadcast=True)
        self.scan_values = self.min_volt + np.arange(0, self.steps) * (self.max_volt - self.min_volt) / (self.steps-1)
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
        print('End of scan.')

        print('saving data ...')
        save_all_data(self)
        self.config_dict.append({'par': 'Status', 'val': True, 'cmt': 'Run finished.'})
        save_config(self.basefilename, self.config_dict)
        add_scan_to_list(self)
        print('Scan' + self.basefilename + ' finished, file saved.')

    @kernel
    def set_mesh_voltage(self, voltage):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(31, 65000)
        self.zotino0.write_dac(31, 1.0/198.946 * (voltage + 14.6027))
        self.zotino0.load()

        return


    def data_check(self, current_step):

        result = np.array(self.get_dataset('scan_result'))
        if (current_step < 11) and (current_step > 0):
            checkee = result[0:current_step]
            avg = checkee.mean()
            std = checkee.std()
            if (result[current_step] < avg+3*std):
                current_step += 1
            else:
                print('An abnormal data detected, redoing ...')

        elif current_step >= 11:
            checkee = result[current_step-10:current_step]
            avg = checkee.mean()
            std = checkee.std()
            if (result[current_step] < avg+3*std):
                current_step += 1
            else:
                print('An abnormal data detected, redoing ...')

        else:
            current_step += 1
        
        return current_step

    @kernel
    def run(self):

        current_step = 0
        while (current_step < self.steps):
            print(current_step, self.scan_values[current_step])
            self.set_mesh_voltage(1/200*self.scan_values[current_step])
            ev = self.ttl3.gate_rising(self.time_count*s)
            ct = self.ttl3.count(ev)
            self.mutate_dataset('scan_result', current_step, ct)
            currrent_step = self.data_check(current_step)
