from artiq.experiment import *
import numpy as np

import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *
from dc_electrodes import *

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")
from bk_4053 import BK4053
from rs_scan import RS

class Scan_Multipoles(EnvExperiment):

    def build(self):

        self.config_dict = []
        
        #self.bk4053 = BK4053()
        self.ext_pulser  = BK4053() # Two pulsers: BK4053 (negative pulse) and DG4162 (positive pulse)
        self.RF_driver = RS()

        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl4') # For sending beginning signal
        self.setattr_device('ttl6') # For triggering RF
        self.setattr_device('ttl11') # For triggering AOM and extraction pulse
        self.setattr_device('scheduler')
        self.setattr_device('zotino0') # For setting voltages of the mesh and DC electrodes

        self.my_setattr('mesh_voltage', NumberValue(default=200,unit='V',min=0,max=600,scale=1,ndecimals=1,step=1))

        # Setting parameters for the histogram
        self.my_setattr('bin_width', NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1))
        #self.my_setattr('number_of_bins', NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))
        
        # Setting time parameters of the experiment
        self.my_setattr('detection_time', NumberValue(default=250,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('extraction_time', NumberValue(default=60,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('load_time', NumberValue(default=200,unit='us',scale=1,ndecimals=0,step=1))
        self.my_setattr('no_of_repeats', NumberValue(default=100000,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('flip', EnumerationValue(['Y', 'N'],default='N'))

        self.my_setattr('multipole_scan', EnumerationValue(['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5'],default='U2'))
        self.my_setattr('minimum', NumberValue(default=-0.69,unit='',min=-0.69,max=0.69,scale=1,ndecimals=2,step=0.01))
        self.my_setattr('maximum', NumberValue(default=0.69,unit='',min=-0.69,max=0.69,scale=1,ndecimals=2,step=0.01))
        self.my_setattr('steps', NumberValue(default=35,unit='',scale=1,ndecimals=0,step=1))

        # Setting RF configurations
        self.my_setattr('RF_frequency',NumberValue(default=1.5762,unit='GHz',scale=1,ndecimals=4,step=.0001))
        self.my_setattr('RF_amplitude',NumberValue(default=5,unit='dBm',scale=1,ndecimals=1,step=.1))

        self.my_setattr('Ex', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('Ey', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('Ez', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))

        self.my_setattr('U1', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U2', NumberValue(default=-0.69,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U3', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U4', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
        self.my_setattr('U5', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))

        if self.flip == 'N':
            self.electrodes = Electrodes()
        else:
            self.electrodes = Flipped_Electrodes()


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

        self.scan_values = np.linspace(self.minimum, self.maximum, self.steps)
        print(self.minimum)
        self.set_dataset('scan_result', [0.0] * self.steps, broadcast=True)
        self.set_dataset('scan_x', self.scan_values, broadcast=True)
        self.set_dataset('arr_of_timestamps',       [ [] ] * self.steps, broadcast=True)
        self.set_dataset('timestamps', [], broadcast=True)

        self.hist_data = []

        self.config_dict.append({'par': 'sequence_file', 'val': os.path.abspath(__file__), 'cmt': 'Filename of the main sequence file'})
        get_basefilename(self)

        # Compute the voltages of DC electrodes we want
        self.multipole_vector = {
                'Ex' : self.Ex,
                'Ey' : self.Ey,
                'Ez' : self.Ez,
                'U1' : self.U1,
                'U2' : self.U2,
                'U3' : self.U3,
                'U4' : self.U4,
                'U5' : self.U5
            }
        print('Vector Defined!')
        (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
        print('Voltages Computed!')
        print('chans:', chans)
        print('voltages:', voltages)
        self.set_electrode_voltages(chans, voltages)
        print('Electrode voltages applied!')

        self.data_to_save = [{'var' : 'arr_of_timestamps', 'name' : 'array of timestamps'},
                             {'var': 'scan_x', 'name': 'scan_x'},
                             {'var': 'scan_result', 'name': 'counts'}]

        # Settings of the R&S SMB100A RF generator (trap RF drive)
        self.RF_driver.set_freq(self.RF_frequency*1e+9)
        self.RF_driver.set_ampl(self.RF_amplitude)

        ## set the extraction pulse
        #self.extraction_time = int(0.9 * self.detection_time)
        #bk4053_freq = 1e6 / (self.detection_time+100)
        #self.bk4053.set_carr_freq(2, bk4053_freq)
        #self.bk4053.set_carr_freq(1, bk4053_freq)
        #self.bk4053.set_carr_delay(2, (self.extraction_time+0.15) * 1e-6)
        #self.bk4053.set_carr_width(1, bk4053_freq, self.load_time*1e-6)

        # set the extraction pulse
        ext_pulser_freq = 1e6 / (self.detection_time+100)
        self.ext_pulser.set_carr_freq(2, ext_pulser_freq)
        self.ext_pulser.set_carr_delay(2, (self.extraction_time+0.15) * 1e-6)

        self.core.reset()
        self.set_mesh_voltage(self.mesh_voltage)
        print('Sleeping for 1 seconds ...')
        time.sleep(1)


    def analyze(self):

        print('Setting mesh voltage to 0V ...')
        self.set_mesh_voltage(0.0)

        print('Setting multipoles to 0')
        self.multipole_vector = {
                'Ex' : 0,
                'Ey' : 0,
                'Ez' : 0,
                'U1' : 0,
                'U2' : 0,
                'U3' : 0,
                'U4' : 0,
                'U5' : 0
            }
        (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
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
                    t_start = now_mu()
                    t_end = self.ttl3.gate_rising(self.detection_time*us)

                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time*us)

                # Extraction pulse
                with sequential:
                    delay(self.extraction_time * us)
                    self.ttl6.pulse(1*us)

            self.read_timestamps(t_start, t_end, i)


    def run(self):

        for k in range(self.steps):

            self.scheduler.pause()

            self.multipole_vector[self.multipole_scan] = self.scan_values[k]
            print('Setting ' + self.multipole_scan + ' to ' + str(self.scan_values[k]))
            (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
            print('chans:', chans)
            print('voltages:', voltages, '\n')
            self.set_electrode_voltages(chans, voltages)
            
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
            self.mutate_dataset('scan_result', k, cts) 
            self.mutate_dataset('arr_of_timestamps', k, self.get_dataset('timestamps')) 

            # reset timestamps
            self.set_dataset('timestamps', [], broadcast=True)

