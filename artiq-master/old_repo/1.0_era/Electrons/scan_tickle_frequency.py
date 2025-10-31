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
from rigol import Rigol_DSG821


class Scan_Tickle_Frequency(EnvExperiment):
    
    def build(self):

        self.bk4053  = BK4053()
        self.tickler = Rigol_DSG821()

        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl4') # For sending beginning signal
        self.setattr_device('ttl6') # For triggering RF
        self.setattr_device('ttl11') # For triggering AOM and extraction pulse
        
        self.setattr_device('ttl8') # For tickle pulse
        
        self.setattr_device('scheduler')
        self.setattr_device('zotino0') # For setting voltages of the mesh and DC electrodes

        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=350,unit='V',scale=1,ndecimals=0,step=1))

        # Setting parameters for the histogram
        self.my_setattr('bin_width', NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1))
        #self.my_setattr('number_of_bins', NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))
        
        # Setting time parameters of the experiment
        self.my_setattr('extraction_time', NumberValue(default=250,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('load_time', NumberValue(default=200,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('no_of_repeats', NumberValue(default=10000,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('flip', EnumerationValue(['Y', 'N'],default='N'))

        self.my_setattr('min_scan', NumberValue(default=1,unit='MHz',scale=1,ndecimals=3,step=.001))
        self.my_setattr('max_scan', NumberValue(default=1000,unit='MHz',scale=1,ndecimals=3,step=.001))
        self.my_setattr('steps', NumberValue(default=20,unit='steps to scan',scale=1,ndecimals=0,step=1))
        
        self.my_setattr('tickle_level', NumberValue(default=-10,unit='dBm',scale=1,ndecimals=1,step=1))
        self.my_setattr('tickle_pulse_length', NumberValue(default=10,unit='us',scale=1,ndecimals=1,step=1))
        
        self.my_setattr('Ex', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('Ey', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('Ez', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))

        self.my_setattr('U1', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U2', NumberValue(default=-0.2,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U3', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U4', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U5', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))

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

        # detect during the extraction pulse

        self.detection_time = int(self.extraction_time - 5*us)

        # Scan interval
        self.scan_values = np.linspace(self.min_scan, self.max_scan, self.steps)

        # Create the dataset of the result
        self.set_dataset('timestamps', [], broadcast=True)
        
        self.set_dataset('arr_of_setpoints', self.scan_values, broadcast=True)
        self.set_dataset('arr_of_timestamps',       [ [] ] * self.steps, broadcast=True)
        
        self.set_dataset('spectrum',       [0] * self.steps, broadcast=True)

        self.hist_data = []

        # Compute the voltages of DC electrodes we want
        self.multipole_vector = {
                'Ex' : self.Ex, #0,
                'Ey' : self.Ey, #0,
                'Ez' : self.Ez, #0,
                'U1' : self.U1, #0,
                'U2' : self.U2, #-0.69,
                'U3' : self.U3, #0,
                'U4' : self.U4, #0,
                'U5' : self.U5  #0
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
        print('Presets done!')
        
        #Set the data going to save
        self.data_to_save = [
                {'var' : 'arr_of_timestamps', 'name' : 'array of timestamps'},
                {'var' : 'arr_of_setpoints', 'name' : 'array of setpoints'},
                {'var' : 'spectrum', 'name' : 'array of trapped electron counts'}
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

            self.core.break_realtime()

            with parallel:

                # Overall start TTL of sequence
                self.ttl4.pulse(2*us)

                # Gate counting to count MCP pulses
                with sequential:
                    
                    # detect during extraction time only

                    delay(self.detection_time * us)

                    # detect for 5 us
                    t_start = now_mu()
                    t_end = self.ttl3.gate_rising(20 * us)

                    #t_start = now_mu()
                    #t_end = self.ttl3.gate_rising(self.detection_time*us)


                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time*us)

                # Extraction pulse
                with sequential:
                    delay(self.extraction_time * us)
                    self.ttl6.pulse(1*us)

                # Tickling pulse
                with sequential:
                    delay(self.load_time * us)
                    delay(5 * us)
                    self.ttl8.pulse(self.tickle_pulse_length * us)

            self.read_timestamps(t_start, t_end, i)


    def run(self):

        ## set aom pulse length
        #self.bk4053.set_carr_freq(2, bk4053_freq)

        self.tickler.on()
        
        for my_ind in range(len(self.scan_values)):

            print("Tickle frequency: {0:.3f} MHz".format(self.scan_values[my_ind]))

            self.scheduler.pause()

            #self.extraction_time = int(0.9 * self.detection_time)
            
            # set the extraction pulse
            bk4053_freq = 1e6 / (self.detection_time+100)
            self.bk4053.set_carr_freq(2, bk4053_freq)
            self.bk4053.set_carr_delay(2, (self.extraction_time+0.15) * 1e-6)

            # apply CW tickle pulse
            self.tickler.set_level(self.tickle_level)
            self.tickler.set_freq(self.scan_values[my_ind])

            # extraction
            self.run_histogram()

            # update data
            self.mutate_dataset('arr_of_timestamps', my_ind, self.get_dataset('timestamps')) 
            xs = self.get_dataset('hist_xs')
            ys = self.get_dataset('hist_ys')
            ind_l = (xs > (self.extraction_time - 2 / self.bin_width))[:-1]
            ind_u = (xs < (self.extraction_time + 4 / self.bin_width))[:-1]
            cts = np.sum(ys[ind_l*ind_u])
            self.mutate_dataset('spectrum', my_ind, cts) 
            #self.mutate_dataset('spectrum', my_ind, np.sum(ys[hlp_ind[0][:-1]]))

            # reset timestamps
            self.set_dataset('timestamps', [], broadcast=True)

        self.tickler.off()


