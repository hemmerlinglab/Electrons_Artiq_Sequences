'''Zijue Luo: Trying to plot histogram of electrons' arrival time and accumulate it for a long time,
extraction pulses were sent to the trap or mesh, lasers were locked asychronously on 1041_RGA'''

from artiq.experiment import *
import numpy as np
from math import ceil

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

class Long_term_hist(EnvExperiment):

    def build(self):

        self.config_dict = []
        
        self.setattr_device('core')
        self.setattr_device('ttl8') # Start trigger
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl11') # For triggering extraction pulses
        self.setattr_device('zotino0') # For controlling mesh voltage

        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=150,unit='V',scale=1,ndecimals=0,step=1))

        # Setting experiment parameters
        self.my_setattr('detection_time', NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('no_of_repeats', NumberValue(default=100000,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('extraction_time', NumberValue(default=2,unit='us',scale=1,ndecimals=0,step=1))

        # Setting histogram paramenter
        self.my_setattr('number_of_bins', NumberValue(default=200,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))

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
        #for k in [0,1]:

            self.zotino0.write_gain_mu(channel_list[k], 65000)
            self.zotino0.load()
            delay(200*us)
            self.zotino0.write_dac(channel_list[k], voltage_list[k])
            self.zotino0.load()
            delay(200*us)

        return

    def prepare(self):

        self.set_dataset('timestamps', [0.0], broadcast=True)
        #self.delay_time = 0.5 # unit is us

        self.channels = np.arange(0, 32)
        self.voltages = np.zeros(len(self.channels))

        self.data_to_save = [{'var': 'timestamps', 'name': 'timestamps'}]

        self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})
        get_basefilename(self)

        self.core.reset()

    def analyze(self):

        print('Saving data ...')
        save_all_data(self)

        # overwrite config file with complete configuration
        self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
        save_config(self.basefilename, self.config_dict)

        add_scan_to_list(self)
        
        print('Scan ' + self.basefilename + ' finished.')

        print('Finished.')

    @kernel
    def read_timestamps(self, t_start, t_end, i):

        tstamp = self.ttl3.timestamp_mu(t_end) # Read one timestamp (in machine unit)
        while tstamp != -1:
            timestamp = (self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)) * 1e6
            self.append_to_dataset('timestamps', timestamp)
            tstamp = self.ttl3.timestamp_mu(t_end) # Read another timestamp

        if (i+1) % self.histogram_refresh == 0:
            self.make_histogram()

        return

    def make_histogram(self):
        
        extract = list(self.get_dataset('timestamps'))
        hist_data = extract[1:len(extract)]
        a, b = np.histogram(extract, bins = np.linspace(0, self.detection_time, self.number_of_bins))

        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)

        return

    @kernel
    def run(self):

        self.set_electrode_voltages(self.channels, self.voltages)
        
        self.set_mesh_voltage(self.mesh_voltage)

        for i in range(self.no_of_repeats):


            self.core.break_realtime() # Prevents RTIO Underflow

            with parallel:
                with sequential:
                    # start trigger of sequence
                    delay(0.1*us)
                    self.ttl8.pulse(1*us) # Extraction pulse
                
                with sequential:
                    #delay((self.extraction_time-self.delay_time)*us) # Set extraction time

                    delay(self.extraction_time*us)
                    self.ttl11.pulse(2*us) # Extraction pulse
                
                with sequential:
                    t_start = now_mu()
                    t_end = self.ttl3.gate_rising(self.detection_time*us)
                    self.read_timestamps(t_start, t_end, i)


