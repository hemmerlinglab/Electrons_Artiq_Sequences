from artiq.experiment import *
import numpy as np
import socket
import time
import sys

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *
from dc_electrodes import *

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")
from bk_4053 import BK4053
from rs_scan import RS

class Scan_Load_Time(EnvExperiment):
    
    def build(self):

        self.bk4053 = BK4053()
        self.RF_driver = RS()

        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl4') # For sending beginning signal
        self.setattr_device('ttl6') # For triggering RF
        self.setattr_device('ttl11') # For triggering AOM and extraction pulse
        self.setattr_device('scheduler')
        self.setattr_device('zotino0') # For setting voltages of the mesh and DC electrodes

        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=200,unit='V',scale=1,ndecimals=0,step=1))

        # Setting parameters for the histogram
        self.my_setattr('bin_width', NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1))
        #self.my_setattr('number_of_bins', NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))
        
        # Setting time parameters of the experiment
        self.my_setattr('min_t', NumberValue(default=5,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('max_t', NumberValue(default=200,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('steps', NumberValue(default=20,unit='steps to scan',scale=1,ndecimals=0,step=1))
        self.my_setattr('wait_time', NumberValue(default=5,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('no_of_repeats', NumberValue(default=100000,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('flip', EnumerationValue(['Y', 'N'],default='N'))

        # Setting RF configurations
        self.my_setattr('RF_frequency',NumberValue(default=1.5762,unit='GHz',scale=1,ndecimals=4,step=.0001))
        self.my_setattr('RF_amplitude',NumberValue(default=5,unit='dBm',scale=1,ndecimals=1,step=.1))

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

        # Scan interval
        self.scan_values = np.linspace(self.min_t, self.max_t, self.steps)
        self.set_dataset('scan_x', self.scan_values, broadcast=True)
        self.set_dataset('scan_result', [0.0] * self.steps, broadcast=True)
        self.set_dataset('arr_of_timestamps',       [ [] ] * self.steps, broadcast=True)
        self.set_dataset('timestamps', [], broadcast=True)

        self.hist_data = []

        # Compute the voltages of DC electrodes we want
        self.multipole_vector = {
                'Ex' : 0,
                'Ey' : 0,
                'Ez' : 0,
                'U1' : 0,
                'U2' : -0.69,
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

        # Settings of the R&S SMB100A RF generator (trap RF drive)
        self.RF_driver.set_freq(self.RF_frequency*1e+9)
        self.RF_driver.set_ampl(self.RF_amplitude)
        
        print('Presets done!')
        
        #Set the data going to save
        self.data_to_save = [
                {'var' : 'arr_of_timestamps', 'name' : 'array of timestamps'},
                {'var' : 'scan_x', 'name' : 'array of load times'},
                {'var' : 'scan_result', 'name' : 'array of trapped electrons counts'}
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
        number_of_bins = int(self.detection_time / self.bin_width)
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
                self.ttl11.pulse(2*us)

                with sequential:
                    t_start = now_mu()
                    t_end = self.ttl3.gate_rising(self.detection_time*us)

                #with sequential:
                #    delay(self.extraction_time * us)
                #    self.ttl6.pulse(1*us)

            self.read_timestamps(t_start, t_end, i)


    def run(self):
        
        for my_t_ind in range(len(self.scan_values)):

            print("Load time: {0:.2f} us".format(self.scan_values[my_t_ind]))

            self.scheduler.pause()

            self.load_time = self.scan_values[my_t_ind]
            self.extraction_time = self.load_time + self.wait_time
           
            # set detection time 10% longer than extraction pulse
            self.detection_time = max(int(1.1 * self.extraction_time), 60)

            # set the extraction pulse
            bk4053_freq = 1e6 / (self.detection_time+100)
            self.bk4053.set_carr_freq(2, bk4053_freq)
            self.bk4053.set_carr_freq(1, bk4053_freq)
            self.bk4053.set_carr_delay(2, (self.extraction_time+0.15) * 1e-6)
            self.bk4053.set_carr_width(1, bk4053_freq, self.load_time*1e-6)

            # extraction
            self.run_histogram()

            # update data
            xs = self.get_dataset('hist_xs')
            ys = self.get_dataset('hist_ys')
            ind_l = (xs > (self.extraction_time - 1 / self.bin_width))[:-1]
            ind_u = (xs < (self.extraction_time + 3 / self.bin_width))[:-1]
            print(ys[ind_l*ind_u])
            cts = np.sum(ys[ind_l*ind_u])
            print(cts)
            self.mutate_dataset('scan_result', my_t_ind, cts) 
            self.mutate_dataset('arr_of_timestamps', my_t_ind, self.get_dataset('timestamps')) 

            # reset timestamps
            self.set_dataset('timestamps', [], broadcast=True)

