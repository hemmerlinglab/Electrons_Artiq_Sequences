'''Zijue Luo: Trying to build the time sequence for trapping, data saving is disabled currently'''

from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

from dc_electrodes import *

class Trapping2(EnvExperiment):
    
    def build(self):
        
        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl8') # For triggering AOM
        self.setattr_device('ttl9') # For triggering RF signal used in trapping
        self.setattr_device('ttl10') # For triggering electrons extraction pulse
        self.setattr_device('scheduler')
        self.setattr_device('zotino0') # For setting voltages of the mesh and DC electrodes

        # Setting the lock frequency for 422 and 390
        self.my_setattr('frequency_422', NumberValue(default=709.078540,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('frequency_390', NumberValue(default=768.824120,unit='THz',scale=1,ndecimals=6,step=1e-6))
        
        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=150,unit='V',scale=1,ndecimals=0,step=1))

        # Setting parameters for the histogram
        self.my_setattr('number_of_bins', NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('max_loop_data', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))

        # Setting time parameters of the experiment
        self.my_setattr('load_time', NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('wait_time', NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('detection_time', NumberValue(default=30,unit='us',scale=1,ndecimals=0,step=1))

        self.electrodes = Electrodes()

        return


    def my_setattr(self, arg, val):
        
        # define the attribute
        self.setattr_argument(arg,val)

        # add each attribute to the config dictionary
        if hasattr(val, 'unit'):
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'unit' : '" + str(val.unit) + "'})")
        else:
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + "})")


    @kernel
    def set_mesh_voltage(self, voltage):
        
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(31, 65000) # Channel 31 for triggering the high voltage goes to the mesh
        self.zotino0.write_dac(31, 1.0/200.0 * voltage)
        self.zotino0.load()


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
        
        # Create the dataset of the result
        self.set_dataset('bin_times', [0], broadcast=True)
        self.hist_data = []

        # Extraction pulses to the zotino
        
        # Set the data going to save
#        self.data_to_save = [{'var' : 'set_points', 'name' : 'set_points'},
#                             {'var' : 'act_freqs', 'name' : 'act_freqs'},
#                             {'var' : 'scan_result', 'name' : 'counts'}]

        # save sequence file name
#        self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})

 #       get_basefilename(self)

        self.core.reset() # Reset the core


#    def analyze(self):
        
#        print('saving data...')
#        save_all_data(self)

        # overwrite config file with complete configuration
#        self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
#        save_config(self.basefilename, self.config_dict)

#        add_scan_to_list(self)
        
#        print('Scan ' + self.basefilename + ' finished.')
#        print('Scan finished.')


    def set_single_laser(self, channel, frequency):
        
        # Channel 5 = 422, Channel 6 = 390
        # Sample message is like 5: 709.077801000

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('192.168.42.136', 63700)

        print('sending new setpoint to channel ' + str(channel) + ': ' + str(frequency) + 'THz')
        sock.connect(server_address)
        
        my_str = str(channel) + ": {0:.9f}".format(frequency)

        #print(my_str)
        #print(my_str.encode())
        try:
            sock.sendall(my_str.encode())

        finally:

            sock.close()
        
        return


    def make_histogram(self, loop):
        extract = list(self.get_dataset('bin_times'))

        # use extract[1:len(extract)] to discard the 0 placed when doing initilization and reset
        if loop < self.max_loop_data:
            self.hist_data.append(extract[1:len(extract)])
        else:
            self.hist_data[loop % self.max_loop_data] = extract[1:len(extract)]
        
        flatten_data = sum(self.hist_data, []) # flatten 2D list self.hist_data to 1D list
        a, b = np.histogram(flatten_data, bins = np.linspace(0, self.detection_time, self.number_of_bins))
        
        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)


    @kernel
    def read_timestamps(self, t_start, t_end, loop):
        tstamp = self.ttl3.timestamp_mu(t_end)
        while tstamp != -1:
            timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
            timestamp_us = timestamp * 1e6
            self.append_to_dataset('bin_times', timestamp_us) # store the timestamps in microsecond
            tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

        self.make_histogram(loop)
        self.set_dataset('bin_times', [0], broadcast=True) # reset with empty list is not allowed, so place a zero in it
        return


    @kernel
    def trapping(self, loop):

        # Time sequence for the experiment
        with parallel:
            # enable detection
            with sequential:
                t_start = now_mu()
                t_end = self.ttl3.gate_rising(self.detection_time*us)
            # send triggering pulses
            with sequential:
                self.ttl8.pulse(1*us)
                delay((self.load_time-1)*us)
                self.ttl9.pulse(1*us)
                dalay((self.wait_time-1)*us)
                self.ttl10.pulse(20*ns)

        # read detected data and generate histogram
        self.read_timestamps(t_start, t_end, loop)


    def run(self):
        
        # Compute the voltages of DC electrodes we want
        self.multipole_vector = {
                'Ex' : 0,
                'Ey' : 0,
                'Ez' : 0,
                'U1' : 0,
                'U2' : -0.65,
                'U3' : 0,
                'U4' : 0,
                'U5' : 0
            }
        (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
        
        # Lock the frequency of 422 and 390
        self.set_single_laser(5, self.frequency_422)
        self.set_single_laser(6, self.frequency_390)

        # Set voltage of the mesh and DC electrodes
        self.set_mesh_voltage(self.mesh_voltage)
        self.set_electrode_voltages(chans, voltages)

        # Time Sequence
        loop = 0
        while True:
            self.trapping(loop)
            loop += 1



