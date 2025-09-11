from artiq.experiment import *
import numpy as np
import sys

# instruments
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")
from bk_4053 import BK4053
from rigol   import DSG821
from rs      import RS

# something within the same directory
from dc_electrodes import Electrodes
from base_sequences import set_multipoles, update_detection_time, set_mesh_voltage, set_MCP_voltages, set_extraction_pulse, set_loading_pulse
from helper_functions import get_basefilename, save_all
from scan_functions import scan_parameter

list_of_traps = ["Single PCB", "UCB 3 PCB"]

#####################################################################
## -1. Set Attribute with config saving  ############################
#####################################################################

def my_setattr(self, arg, val, scanable = True):
    
    # define the attribute
    self.setattr_argument(arg, val)

    # add each attribute to the config dictionary
    if hasattr(val, 'unit'):
        exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'unit' : '" + str(val.unit) + "', 'scanable' : " + str(scanable) + "})")
    else:
        exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'scanable' : " + str(scanable) + "})")

    return

#####################################################################
## -2. Build  #######################################################
#####################################################################

# 1) Master function for build
def base_build(self):

    load_variables(self)
    load_attributes(self)
    load_parameters(self)

    return

# 2) Subfunctions for build
def load_variables(self):

    self.config_dict = []
    self.wavemeter_frequencies = []

    return

def load_attributes(self):

    self.setattr_device('core')
    self.setattr_device('ttl3')      # For inputing MCP signals
    self.setattr_device('ttl4')      # For sending beginning signal
    self.setattr_device('ttl6')      # For triggering RF
    self.setattr_device('ttl11')     # For triggering AOM and extraction pulse
    
    self.setattr_device('ttl8')      # For tickle signal ON/OFF
    
    self.setattr_device('scheduler') # For "Terminate Instances" from Dashboard
    self.setattr_device('zotino0')   # For setting voltages of the mesh and DC electrodes

    return

def load_parameters(self):

    # 1. Detection Mode Settings
    #------------------------------------------------------
    my_setattr(self, 'histogram_on', BooleanValue(default=True), scanable=False)
    my_setattr(self, 'short_detection', BooleanValue(default=False), scanable = False)

    # 2. Display Settings
    #------------------------------------------------------
    my_setattr(self, 'bin_width', NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1), scanable = False)
    my_setattr(self, 'histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1), scanable = False)

    # 3. Detector Settings
    #------------------------------------------------------
    my_setattr(self, 'mesh_voltage', NumberValue(default=150,unit='V',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'MCP_front', NumberValue(default=300,unit='V',scale=1,ndecimals=0,step=1))

    # 4. Sequence Settings
    #------------------------------------------------------
    my_setattr(self, 'wait_time', NumberValue(default=40,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'load_time', NumberValue(default=300,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'no_of_repeats', NumberValue(default=10000,unit='',scale=1,ndecimals=0,step=1))

    # 5. Trap Settings
    #------------------------------------------------------
    my_setattr(self, 'trap', EnumerationValue(list_of_traps, default = list_of_traps[0]), scanable = False)
    my_setattr(self, 'flip_electrodes', BooleanValue(default=False))

    # 6. Laser Settings
    #------------------------------------------------------
    my_setattr(self, 'frequency_422', NumberValue(default=709.078240,unit='THz',scale=1,ndecimals=6,step=1e-6))
    my_setattr(self, 'frequency_390', NumberValue(default=766.928560,unit='THz',scale=1,ndecimals=6,step=1e-6))

    # 7. Tickle Settings
    #------------------------------------------------------
    my_setattr(self, 'tickle_level', NumberValue(default=-5,unit='dBm',scale=1,ndecimals=1,step=1))
    my_setattr(self, 'tickle_frequency', NumberValue(default=64,unit='MHz',scale=1,ndecimals=4,step=.0001))
    my_setattr(self, 'tickle_pulse_length', NumberValue(default=50,unit='us',scale=1,ndecimals=1,step=1))
    my_setattr(self, 'tickle_on', BooleanValue(default=False), scanable = False)

    # 8. RF Settings
    #------------------------------------------------------
    my_setattr(self, 'RF_amplitude',NumberValue(default=8,unit='dBm',scale=1,ndecimals=1,step=.1))
    my_setattr(self, 'RF_frequency',NumberValue(default=1.761,unit='GHz',scale=1,ndecimals=4,step=.0001))

    # 9. Extraction Pulse Settings
    #------------------------------------------------------
    my_setattr(self, 'ext_pulse_length', NumberValue(default=900,unit='ns',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'ext_pulse_amplitude', NumberValue(default=10,unit='V',scale=1,ndecimals=2,step=.01))

    # 10. DC Settings
    #------------------------------------------------------
    # 1) 1st Order Multipoles
    my_setattr(self, 'Ex', NumberValue(default=0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'Ey', NumberValue(default=-0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'Ez', NumberValue(default=0,unit='V',scale=1,ndecimals=3,step=.001))
    # 2) 2nd Order Multipoles
    my_setattr(self, 'U1', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U2', NumberValue(default=-0.45,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U3', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U4', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U5', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))

    # 11. Scan Settings
    #------------------------------------------------------
    list_of_parameters = [x['par'] for x in self.config_dict if x['scanable']]
    my_setattr(self, 'scanning_parameter', EnumerationValue(list_of_parameters, default = list_of_parameters[0]))
    my_setattr(self, 'min_scan', NumberValue(default=100,unit='',scale=1,ndecimals=4,step=.0001))
    my_setattr(self, 'max_scan', NumberValue(default=200,unit='',scale=1,ndecimals=4,step=.0001))
    my_setattr(self, 'steps', NumberValue(default=100,unit='steps to scan',scale=1,ndecimals=0,step=1))
    
    return

#####################################################################
## -2. Prepare  #####################################################
#####################################################################

# 1) Master function for prepare
def my_prepare(self):

    prepare_instruments(self)
    prepare_datasets(self)
    prepare_initialization(self)
    prepare_saving_configuration(self)

    return

# 2) Subfunctions for prepare
def prepare_instruments(self):

    self.ext_pulser = BK4053()  # extraction pulse generator
    self.tickler    = DSG821()  # tickle pulse generator
    self.RF_driver  = RS()      # trap drive

    # Zotino DC controller
    self.electrodes = Electrodes(trap = self.trap, flipped = self.flip_electrodes)

    return

def prepare_initialization(self):

    # configures the trap drive, mesh voltage, etc ...

    # 1. Trap drive
    #------------------------------------------------------
    self.RF_driver.set_ampl(self.RF_amplitude)
    self.RF_driver.set_freq(self.RF_frequency * 1e9)

    # 2. DC voltages
    #------------------------------------------------------

    set_multipoles(self)

    # 3. Mesh and MCP voltage
    #------------------------------------------------------
    set_mesh_voltage(self, self.mesh_voltage)

    self.current_MCP_front = self.MCP_front
    set_MCP_voltages(self, self.MCP_front)

    # 4. Extraction Pulse
    #------------------------------------------------------

    # Set the extraction pulse
    set_extraction_pulse(self)

    set_loading_pulse(self)

    # 5. Tickle Pulse
    #------------------------------------------------------

    # Set the tickling pulse
    if self.tickle_on:
        self.tickler.on()
        self.tickler.set_ampl(self.tickle_level)
        self.tickler.set_freq(self.tickle_frequency)
    else:
        self.tickler.off()

    return

def prepare_saving_configuration(self):
    
    # Set the data going to save
    self.data_to_save = [
            {'var' : 'arr_of_timestamps', 'name' : 'array of timestamps during extraction'},
            {'var' : 'arr_of_setpoints', 'name' : 'array of setpoints'},
            {'var' : 'trapped_signal', 'name' : 'array of trapped electron counts'},
            {'var' : 'loading_signal', 'name' : 'array of loading electron counts'},
            {'var' : 'lost_signal', 'name': 'array of kicked out electron counts in the first 15us or during the tickle pulse duration when it is smaller than 15us'},
            {'var' : 'ratio_signal', 'name' : 'array of trapped counts / loading counts'},
            {'var' : 'ratio_lost', 'name' : 'array of lost counts / loading counts'}
            ]

    # save sequence file name

    self.config_dict.append({'par' : 'sequence_file', 'val' : self.sequence_filename, 'cmt' : 'Filename of the main sequence file'})

    get_basefilename(self)

    self.core.reset() # Reset the core

    for k in range(1):
        print("")
    print("*"*100)
    print("* Starting new scan")
    print("*"*100)
    print("")

    return

def prepare_datasets(self):

    update_detection_time(self)
    
    # Scan interval
    self.scan_values = np.linspace(self.min_scan, self.max_scan, self.steps)

    # Check scan range
    self.scan_ok = scan_parameter(self, 0, scan_check = True)

    # Create the dataset of the result

    # timestamps for each sequence iteration
    self.set_dataset('timestamps', [], broadcast=True)
    
    # data sets to save all time stamps
    self.set_dataset('arr_of_setpoints',           self.scan_values, broadcast=True)
    self.set_dataset('arr_of_timestamps',          [ [] ] * self.steps, broadcast=True)
    
    self.set_dataset('trapped_signal',       [0] * self.steps, broadcast=True)
    self.set_dataset('loading_signal',       [0] * self.steps, broadcast=True)
    self.set_dataset('lost_signal',          [0] * self.steps, broadcast=True)
    self.set_dataset('ratio_signal',         [0] * self.steps, broadcast=True)
    self.set_dataset('ratio_lost',           [0] * self.steps, broadcast=True)

    return

#####################################################################
## -3. Analyze  #####################################################
#####################################################################

# 1) Master function for analyze
def my_analyze(self):

    # reset scan value to setting in parameter

    reset_scan_parameter(self)

    if self.scan_ok:

        print('Saving data...')
        save_all(self)
        print('Experiment ' + self.basefilename + ' finished.')
        print('Experiment finished.')

    else:

        print('Scan terminated.')

    return
    
# 2) Subfunctions for analyze
def reset_scan_parameter(self):
    
    # sets the value of the scanned parameter to the one in the parameter listing

    scan_parameter(self, 0, reset_value = True)

    return


