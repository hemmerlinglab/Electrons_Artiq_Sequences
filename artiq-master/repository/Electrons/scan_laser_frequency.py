'''Zijue Luo: Scan frequencies of 390 and 422 without sending trigger signals'''

from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

class Scan_laser_frequencies(EnvExperiment):

    def build(self):

        self.config_dict = [] # For saving config of the experiment
        self.wavemeter_frequencies = [] # For saving actual frequencies

        self.setattr_device('core')
        self.setattr_device('ttl3') # For reading MCP signals
        self.setattr_device('zotino0') # For setting mesh voltage

        self.setattr_device('scheduler') # For setting up 'terminate instances' functionality

        # Setting the lock frequency and scan range
        self.my_setattr('frequency_422', NumberValue(default=709.078710,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('frequency_390', NumberValue(default=766.819450,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('scanning_laser', EnumerationValue(['422', '390'],default='390'))
        self.my_setattr('min_freq', NumberValue(default=-1000,unit='MHz',scale=1,ndecimals=0,step=1))
        self.my_setattr('max_freq', NumberValue(default=1000,unit='MHz',scale=1,ndecimals=0,step=1))
        self.my_setattr('steps', NumberValue(default=20,unit='steps to scan',scale=1,ndecimals=0,step=1))

        # Setting laser lock parameters
        self.my_setattr('relock_steps', NumberValue(default=4,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('lock_wait_time', NumberValue(default=1000,unit='ms',scale=1,ndecimals=0,step=1))
        self.my_setattr('relock_wait_time', NumberValue(default=4000,unit='ms',scale=1,ndecimals=0,step=1))

        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=120,unit='V',scale=1,ndecimals=0,step=1))

        # Setting counting related configs
        self.my_setattr('no_of_repeats', NumberValue(default=100,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('detection_time', NumberValue(default=1000,unit='us',scale=1,ndecimals=0,step=1))

    def my_setattr(self, arg, val):

        self.setattr_argument(arg, val) # Define the attribute

        # Add the attribute to config_dict
        if hasattr(val, 'unit'):
            exec("self.config_dict.append({'par': arg, 'val': self." + arg + ", 'unit': '" + str(val.unit) + "'})")
        else:
            exec("self.config_dict.append({'par': arg, 'val': self." + arg + "})")

    @kernel
    def set_mesh_voltage(self, voltage):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(31, 65000)
        self.zotino0.write_dac(31, 1.0/198.946 * (voltage + 14.6027))
        self.zotino0.load()

        return


    def prepare(self):

        # Calculate the frequencies for scanning
        if self.scanning_laser == '390':
            self.scan_values = self.frequency_390 + 1e-6 * np.linspace(self.min_freq, self.max_freq, self.steps)
        elif self.scanning_laser == '422':
            self.scan_values = self.frequency_422 + 1e-6 * np.linspace(self.min_freq, self.max_freq, self.steps)

        # Create the dataset of the result
        self.set_dataset('set_points', self.scan_values, broadcast=True)
        self.set_dataset('act_freqs', [0] * len(self.scan_values), broadcast=True)
        self.set_dataset('scan_result', [0.0] * len(self.scan_values), broadcast=True)

        # Set the data going to save
        self.data_to_save = [{'var' : 'set_points', 'name' : 'set_points'},
                             {'var' : 'act_freqs', 'name' : 'act_freqs'},
                             {'var' : 'scan_result', 'name' : 'counts'}]

        # save sequence file name
        self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})
        get_basefilename(self)

        self.core.reset() # Reset the core

    @kernel
    def counting(self):

        # Preparation
        self.core.break_realtime() # To avoid RTIO Underflow
        data = [0] * self.no_of_repeats
        
        # Counting for self.no_of_repeat times and store the result in a dataset
        for i in range(self.no_of_repeats):
            ev = self.ttl3.gate_rising(self.detection_time*us)
            data[i] = self.ttl3.count(ev)
            delay(0.01*self.detection_time*us)
        self.set_dataset('single_freq_count', (data), broadcast=True)

    def set_single_laser(self, which_laser, frequency, do_switch = False, wait_time = None):
        
        if which_laser == '422':
            channel = 5
        elif which_laser == '390':
            channel = 6

        if do_switch:
            switch = 1
        else:
            switch = 0

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = ('192.168.42.136', 63700)
        print('Sending new setpoint {0:.6f}THz to laser {1}.'.format(frequency, which_laser))
        sock.connect(server_address)
        message = "{0:1d},{1:.9f},{2:1d},{3:3d}".format(int(channel), float(frequency), int(switch), int(wait_time))
        sock.sendall(message.encode())
        sock.close()
        time.sleep(wait_time/1000.0+1)

        return

    def analyze(self):
        
        print('saving data...')
        save_all_data(self)

        # overwrite config file with complete configuration
        self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
        save_config(self.basefilename, self.config_dict)

        add_scan_to_list(self)
        
        print('Scan ' + self.basefilename + ' finished.')
        print('Scan finished.')

    def run(self):

        self.set_mesh_voltage(self.mesh_voltage) # Set the voltage of the mesh

        # Sequence for locking 422 and scanning 390
        if self.scanning_laser == '390':

            # Lock the freqeuncy of 422 and 390 to the initial point
            self.set_single_laser(422, self.frequency_422, do_switch=True, wait_time=self.relock_wait_time)
            self.set_single_laser(390, self.frequency_390+self.min_freq*1e-6, do_switch=True, wait_time=self.relock_wait_time)

            for i in range(len(self.scan_values)):

                self.scheduler.pause() # Allows for "terminate instances" functionality

                print("{0}/{1}: {2:.6f}".format(i+1, len(self.scan_values), self.scan_values[i]))

                # Set laser frequencies: lock and relock
                if (i+1) % self.relock_steps == 0:
                    print('Relocking 422 ...')
                    self.set_single_laser(422, self.frequency_422, do_switch=True, wait_time=self.relock_wait_time)
                    self.set_single_laser(390, self.scan_values[i], do_switch=True, wait_time=self.relock_wait_time)
                else:
                    self.set_single_laser(390, self.scan_values[i], wait_time=self.lock_wait_time)

                # Count and process the counts
                self.counting()
                cts = np.array(self.get_dataset('single_freq_count'))
                avg_counts = np.mean(cts)

                # Read actual frequency of 390
                self.wavemeter_frequencies = get_laser_frequencies()

                # Store the data in dataset
                self.mutate_dataset('scan_result', i, avg_counts)
                self.mutate_dataset('act_freqs', i, self.wavemeter_frequencies)
                self.mutate_dataset('set_points', i, self.scan_values[i])

        # Sequence for locking 390 and scanning 422
        elif self.scanning_laser == '422':

            # Lock the freqeuncy of 422 and 390 to the initial point
            self.set_single_laser(390, self.frequency_390, do_switch=True, wait_time=self.relock_wait_time)
            self.set_single_laser(422, self.frequency_422+self.min_freq*1e-6, do_switch=True, wait_time=self.relock_wait_time)

            for i in range(len(self.scan_values)):

                self.scheduler.pause() # Allows for "terminate instances" functionality

                print("{0}/{1}: {2:.6f}".format(i, len(self.scan_values), self.scan_values[i]))

                # Set laser frequencies: lock and relock
                if (i+1) % self.relock_steps == 0:
                    print('Relocking 390 ...')
                    self.set_single_laser(390, self.frequency_390, do_switch=True, wait_time=self.relock_wait_time)
                    self.set_single_laser(422, self.scan_values[i], do_switch=True, wait_time=self.relock_wait_time)
                else:
                    self.set_single_laser(422, self.scan_values[i], wait_time=self.lock_wait_time)

                # Count and process the counts
                self.counting()
                cts = np.array(self.get_dataset('single_freq_count'))
                avg_counts = np.mean(cts)

                # Read actual frequency of 422
                self.wavemeter_frequencies = get_laser_frequencies()

                # Store the data in dataset
                self.mutate_dataset('scan_result', i, avg_counts)
                self.mutate_dataset('act_freqs', i, self.wavemeter_frequencies)
                self.mutate_dataset('set_points', i, self.scan_values[i])

