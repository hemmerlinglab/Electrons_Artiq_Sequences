from artiq.experiment import *
import artiq.coredevice.sampler as splr
import numpy as np
import os

import sys
#sys.path.append("/home/molecules/software/Molecules_Artiq_Sequences/artiq-master/repository/helper_functions")

#from helper_functions import *

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")
from dc_electrodes import *
from bk_4053 import BK4053
from rigol import Rigol_DSG821


def my_setattr(self, arg, val):
    
    # define the attribute
    self.setattr_argument(arg,val)

    # add each attribute to the config dictionary
    if hasattr(val, 'unit'):
        exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'unit' : '" + str(val.unit) + "'})")
    else:
        exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + "})")

    return

def base_build(self):

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
    my_setattr(self, 'mesh_voltage', NumberValue(default=350,unit='V',scale=1,ndecimals=0,step=1))

    # Setting parameters for the histogram
    #my_setattr('bin_width', NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1))
    #my_setattr('number_of_bins', NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1))
    #my_setattr('histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))
    
    my_setattr(self, 'extraction_time', NumberValue(default=270,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'load_time', NumberValue(default=200,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'no_of_repeats', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'flip', EnumerationValue(['Y', 'N'],default='N'))

    my_setattr(self, 'min_scan', NumberValue(default=100,unit='MHz',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'max_scan', NumberValue(default=200,unit='MHz',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'steps', NumberValue(default=100,unit='steps to scan',scale=1,ndecimals=0,step=1))
    
    my_setattr(self, 'tickle_level', NumberValue(default=-5,unit='dBm',scale=1,ndecimals=1,step=1))
    my_setattr(self, 'tickle_pulse_length', NumberValue(default=50,unit='us',scale=1,ndecimals=1,step=1))
    
    my_setattr(self, 'Ex', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
    my_setattr(self, 'Ey', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
    my_setattr(self, 'Ez', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))

    my_setattr(self, 'U1', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
    my_setattr(self, 'U2', NumberValue(default=-0.69,unit='V',scale=1,ndecimals=3,step=.01))
    my_setattr(self, 'U3', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
    my_setattr(self, 'U4', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))
    my_setattr(self, 'U5', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.01))

    if self.flip == 'N':
        self.electrodes = Electrodes()
    else:
        self.electrodes = Flipped_Electrodes()

    return

def my_analyze(self):

    print('Saving data...')
    save_all_data(self)

    # overwrite config file with complete configuration
    self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
    save_config(self.basefilename, self.config_dict)

    add_scan_to_list(self)
    
    print('Trap ' + self.basefilename + ' finished.')
    print('Trap finished.')

    return

def my_prepare(self):

    # detect during the extraction pulse
    self.detection_time = int(self.extraction_time - 5*us)

    # Scan interval
    self.scan_values = np.linspace(self.min_scan, self.max_scan, self.steps)

    # Create the dataset of the result
    self.set_dataset('timestamps', [], broadcast=True)
    self.set_dataset('timestamps_loading', [], broadcast=True)
    
    self.set_dataset('arr_of_setpoints', self.scan_values, broadcast=True)
    self.set_dataset('arr_of_timestamps',       [ [] ] * self.steps, broadcast=True)
    self.set_dataset('arr_of_timestamps_loading',       [ [] ] * self.steps, broadcast=True)
    
    self.set_dataset('spectrum',       [0] * self.steps, broadcast=True)

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
    
    #print('Vector Defined!')
    (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
    #print('Voltages Computed!')
    #print('chans:', chans)
    #print('voltages:', voltages)
    
    self.set_electrode_voltages(chans, voltages)
    
    print('Electrode voltages applied!')

    # Set mesh voltages
    self.set_mesh_voltage(self.mesh_voltage)
    print('Mesh voltage already set!')
    print('Presets done!')
    

    # set the extraction pulse
    bk4053_freq = 1e6 / (self.detection_time+100)
    self.bk4053.set_carr_freq(2, bk4053_freq)
    self.bk4053.set_carr_delay(2, (self.extraction_time+0.15) * 1e-6)


    #####################################
    # Saving data configurations
    #####################################
    
    # Set the data going to save
    self.data_to_save = [
            {'var' : 'arr_of_timestamps', 'name' : 'array of timestamps during extraction'},
            {'var' : 'arr_of_timestamps_loading', 'name' : 'array of timestamps during loading'},
            {'var' : 'arr_of_setpoints', 'name' : 'array of setpoints'},
            {'var' : 'spectrum', 'name' : 'array of trapped electron counts'}
            ]

    # save sequence file name

    self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})

    get_basefilename(self)

    self.core.reset() # Reset the core

    return


#####################################################################
# Functions with decorators
#####################################################################


@kernel
def set_mesh_voltage(self, voltage):

    print('Setting mesh voltage')
    
    self.core.break_realtime()
    self.zotino0.init()
    delay(200*us)
    self.zotino0.write_gain_mu(31, 65000)
    self.zotino0.write_dac(31, 1.0/198.946 * (voltage + 14.6027))
    self.zotino0.load()

    return


@kernel
def set_electrode_voltages(self, channel_list, voltage_list):

    print('Setting DC electrode voltages')
    
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


@kernel
def count_events(self):
    
    ind_count = 0
    # Time Sequence
    for i in range(self.no_of_repeats):

        self.core.break_realtime()

        with parallel:

            # Overall start TTL of sequence
            self.ttl4.pulse(2*us)

            # Gate counting to count MCP pulses
            with sequential:

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

        self.read_only_timestamps(t_start, t_end, i)

    return



@kernel
def read_only_timestamps(self, t_start, t_end, i):

    tstamp = self.ttl3.timestamp_mu(t_end)
    while tstamp != -1:
        timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
        timestamp_us = timestamp * 1e6
        self.append_to_dataset('timestamps', timestamp_us) # store the timestamps in microsecond
        tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

    return



