'''Zijue Luo: Trying to build the time sequence for trapping, data saving is disabled currently'''

from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")

from dc_electrodes import *

from bk_4053 import BK4053



class Scan_Extracion_Pulse(EnvExperiment):
    
    def build(self):

        self.bk4053 = BK4053()

        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl4') # For sending beginning signal
        self.setattr_device('ttl6') # For triggering RF
        self.setattr_device('ttl11') # For triggering AOM and extraction pulse
        self.setattr_device('scheduler')
        self.setattr_device('zotino0') # For setting voltages of the mesh and DC electrodes

        # Setting the lock frequency for 422 and 390
        #self.my_setattr('frequency_422', NumberValue(default=709.078540,unit='THz',scale=1,ndecimals=6,step=1e-6))
        #self.my_setattr('frequency_390', NumberValue(default=768.824120,unit='THz',scale=1,ndecimals=6,step=1e-6))
        
        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=200,unit='V',scale=1,ndecimals=0,step=1))

        # Setting parameters for the histogram
        self.my_setattr('bin_width', NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1))
        #self.my_setattr('number_of_bins', NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))
        #self.my_setattr('max_no_of_timestamps', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))

        # Setting time parameters of the experiment
        #self.my_setattr('detection_time', NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('load_time', NumberValue(default=50,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('no_of_repeats', NumberValue(default=100000,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('flip', EnumerationValue(['Y', 'N'],default='N'))


        self.my_setattr('min_t', NumberValue(default=0,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('max_t', NumberValue(default=1000,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('steps', NumberValue(default=20,unit='steps to scan',scale=1,ndecimals=0,step=1))



        if self.flip == 'N':
            self.electrodes = Electrodes()
        else:
            self.electrodes = Flipped_Electrodes()

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

        # Create the dataset of the result
        self.set_dataset('timestamps', [], broadcast=True)
        
        self.set_dataset('arr_of_extraction_times', [0] * self.steps, broadcast=True)
        self.set_dataset('arr_of_timestamps',       [ [] ] * self.steps, broadcast=True)

        self.hist_data = []

        # Laser was locked automatically on 1041RGA, so we do not need to do anything here
        #self.set_single_laser(422, self.frequency_422, do_switch=True)
        #self.set_single_laser(390, self.frequency_390, do_switch=True)

        # Compute the voltages of DC electrodes we want
        self.multipole_vector = {
                'Ex' : 0,
                'Ey' : 0,
                'Ez' : 0,
                'U1' : 0,
                'U2' : -0.3, #-0.69,
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

        
        # Scan interval
        self.scan_values = np.linspace(self.min_t, self.max_t, self.steps)

        print('Presets done!')
        
        #Set the data going to save
        self.data_to_save = [
#                {'var' : 'set_points', 'name' : 'set_points'},
#                {'var' : 'act_freqs', 'name' : 'act_freqs'},
                {'var' : 'timestamps', 'name' : 'timestamps'},
                {'var' : 'arr_of_timestamps', 'name' : 'array of timestamps'},
                {'var' : 'arr_of_extraction_times', 'name' : 'array of extraction times'},
                ]

        # save sequence file name

        self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})

        get_basefilename(self)

        self.core.reset() # Reset the core


    def analyze(self):

        self.set_dataset('all_timestamps', self.hist_data)
        
        print('saving data...')
        save_all_data(self)

        # overwrite config file with complete configuration
        self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
        save_config(self.basefilename, self.config_dict)

        add_scan_to_list(self)
      
        print('Trap ' + self.basefilename + ' finished.')
        print('Trap finished.')


    def make_histogram(self):
        
        # for display
        extract = list(self.get_dataset('timestamps'))
        self.hist_data = extract[1:len(extract)]
        number_of_bins = self.detection_time // self.bin_width
        print(number_of_bins)
        a, b = np.histogram(self.hist_data, bins = np.linspace(0, self.detection_time, number_of_bins))
        
        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)

        return


    @kernel
    def read_timestamps(self, t_start, t_end, i):

        if (i+1) % self.histogram_refresh != 0:
            tstamp = self.ttl3.timestamp_mu(t_end)
            while tstamp != -1:
                timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
                timestamp_us = timestamp * 1e6
                self.append_to_dataset('timestamps', timestamp_us) # store the timestamps in microsecond
                tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

        else:
            self.make_histogram()

        return


    @kernel
    def run_histogram(self):
        
        ind_count = 0
        # Time Sequence
        for i in range(self.no_of_repeats):
#        while True:

            self.core.break_realtime()

            with parallel:

                self.ttl4.pulse(2*us)

                with sequential:
                    t_start = now_mu()
                    t_end = self.ttl3.gate_rising(self.detection_time*us)

                self.ttl11.pulse(self.load_time*us)

                with sequential:
                    delay(self.extraction_time * us)
                    self.ttl6.pulse(1*us)

            self.read_timestamps(t_start, t_end, i)



    def run(self):

        
        for my_t_ind in range(len(self.scan_values)):

            print("Extraction time: {0:.2f} us".format(self.scan_values[my_t_ind]))

            self.scheduler.pause()

            # set the extraction pulse
            self.bk4053.set_carr_delay(self.scan_values[my_t_ind] * 1e-6)

            self.extraction_time = self.scan_values[my_t_ind]
           
            # set detection time 10% longer than extraction pulse
            self.detection_time = int(1.1 * self.scan_values[my_t_ind])

            # extraction
            self.run_histogram()

            # update data

            self.mutate_dataset('arr_of_extraction_times', my_t_ind, self.scan_values[my_t_ind]) 
            
            self.mutate_dataset('arr_of_timestamps', my_t_ind, self.get_dataset('timestamps')) 

            
            # reset timestamps
            self.set_dataset('timestamps', [], broadcast=True)


        #print(self.get_dataset('arr_of_timestamps'))
        #print(self.get_dataset('arr_of_extraction_times'))

