from artiq.experiment import *
import numpy as np
import sys

# instruments within the `drivers` directory
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")
from bk_4053 import BK4053
from rigol   import DSG821
from rs      import RS
from laser_controller import LaserClient

# something within the same directory
from dc_electrodes import Electrodes
from base_sequences import set_multipoles, update_detection_time, set_mesh_voltage, set_MCP_voltages, set_extraction_pulse, set_loading_pulse, get_MCP_voltages
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
    self.setattr_device('sampler0')  # For reading current MCP high voltage control signal

    return

def load_parameters(self):

    # 1. Detection Mode Settings
    #------------------------------------------------------
    my_setattr(self, 'mode',            EnumerationValue(['Trapping', 'Counting'],default='Trapping'), scanable = False)
    my_setattr(self, 'histogram_on',    BooleanValue(default=True), scanable=False)
    my_setattr(self, 'short_detection', BooleanValue(default=False), scanable = False)

    # 2. Display Settings
    #------------------------------------------------------
    my_setattr(self, 'bin_width',         NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1), scanable = False)
    my_setattr(self, 'histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1), scanable = False)

    # 3. Detector Settings
    #------------------------------------------------------
    my_setattr(self, 'mesh_voltage', NumberValue(default=108,unit='V',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'MCP_front',    NumberValue(default=300,unit='V',scale=1,ndecimals=0,step=1))

    # 4. Sequence Settings
    #------------------------------------------------------
    my_setattr(self, 'wait_time',      NumberValue(default=40,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'load_time',      NumberValue(default=300,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'no_of_repeats',  NumberValue(default=10000,unit='',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'detection_time', NumberValue(default=1000,unit='ms for counting mode only',scale=1,ndecimals=0,step=1))

    # 5. Trap Settings
    #------------------------------------------------------
    my_setattr(self, 'trap',            EnumerationValue(list_of_traps,default=list_of_traps[0]), scanable = False)
    my_setattr(self, 'flip_electrodes', BooleanValue(default=False))

    # 6. Laser Settings
    #------------------------------------------------------
    my_setattr(self, 'frequency_422', NumberValue(default=709.078300,unit='THz',scale=1,ndecimals=6,step=1e-6))
    my_setattr(self, 'frequency_390', NumberValue(default=766.928560,unit='THz',scale=1,ndecimals=6,step=1e-6))

    # 7. Tickle Settings
    #------------------------------------------------------
    my_setattr(self, 'tickle_on',           BooleanValue(default=False), scanable = False)
    my_setattr(self, 'tickle_level',        NumberValue(default=-10,unit='dBm',scale=1,ndecimals=1,step=1))
    my_setattr(self, 'tickle_frequency',    NumberValue(default=64,unit='MHz',scale=1,ndecimals=4,step=.0001))
    my_setattr(self, 'tickle_pulse_length', NumberValue(default=50,unit='us',scale=1,ndecimals=1,step=1))

    # 8. RF Settings
    #------------------------------------------------------
    my_setattr(self, 'RF_on', BooleanValue(default=False))
    my_setattr(self, 'RF_amplitude', NumberValue(default=8,unit='dBm',scale=1,ndecimals=1,step=.1))
    my_setattr(self, 'RF_frequency', NumberValue(default=1.738,unit='GHz',scale=1,ndecimals=4,step=.0001))

    # 9. Extraction Pulse Settings
    #------------------------------------------------------
    my_setattr(self, 'ext_pulse_length',    NumberValue(default=900,unit='ns',scale=1,ndecimals=0,step=1))
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
    my_setattr(self, 'min_scan',           NumberValue(default=100,unit='',scale=1,ndecimals=6,step=.000001))
    my_setattr(self, 'max_scan',           NumberValue(default=200,unit='',scale=1,ndecimals=6,step=.000001))
    my_setattr(self, 'steps',              NumberValue(default=100,unit='steps to scan',scale=1,ndecimals=0,step=1))
    
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

    self.ext_pulser = BK4053()      # extraction pulse generator and AOM controller
    self.tickler    = DSG821()      # tickle pulse generator
    self.RF_driver  = RS()          # trap drive
    self.laser      = LaserClient() # Laser Lock GUI client

    # Zotino DC controller
    self.electrodes = Electrodes(trap = self.trap, flipped = self.flip_electrodes)

    return

def prepare_initialization(self):

    # configures the trap drive, mesh voltage, etc ...

    # 1. Laser
    #------------------------------------------------------
    self.laser.set_frequency(390, self.frequency_390)
    self.laser.set_frequency(422, self.frequency_422)

    # 1. Trap drive
    #------------------------------------------------------
    self.RF_driver.set_ampl(self.RF_amplitude)
    self.RF_driver.set_freq(self.RF_frequency * 1e9)
    if self.RF_on:
        self.RF_driver.on()
    else:
        self.RF_driver.off()

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
    set_extraction_pulse(self)
    set_loading_pulse(self)

    # 5. Tickle Pulse
    #------------------------------------------------------
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
            {'var' : 'arr_of_timestamps',  'name' : 'array of timestamps during extraction'},
            {'var' : 'arr_of_setpoints',   'name' : 'array of setpoints'},
            {'var' : 'last_frequency_422', 'name' : 'array of fetched last frequency from laser lock GUI, actual frequency if the GUI is measuring 422 at the time'},
            {'var' : 'last_frequency_390', 'name' : 'array of fetched last frequency from laser lock GUI, actual frequency if the GUI is measuring 390 at the time'},
            {'var' : 'trapped_signal',     'name' : 'array of trapped electron counts'},
            {'var' : 'loading_signal',     'name' : 'array of loading electron counts'},
            {'var' : 'lost_signal',        'name' : 'array of kicked out electron counts in the first 15us or during the tickle pulse duration when it is smaller than 15us'},
            {'var' : 'ratio_signal',       'name' : 'array of trapped counts / loading counts'},
            {'var' : 'ratio_lost',         'name' : 'array of lost counts / loading counts'},
            {'var' : 'scan_x',             'name' : 'array of setpoints for counting mode, duplicate but in order to be compatible with applet'},
            {'var' : 'scan_result',        'name' : 'array of recorded counts for counting mode'},
            {'var' : 'time_cost',          'name' : 'array of time cost for each experiment scan'}
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
    self.set_dataset('timestamps',         [], broadcast=True)
    
    # data sets to save all time stamps
    self.set_dataset('arr_of_setpoints',   self.scan_values, broadcast=True)
    self.set_dataset('arr_of_timestamps',  [ [] for _ in range(self.steps) ], broadcast=True)
    #self.set_dataset('arr_of_timestamps', [ [] ] * self.steps, broadcast=True)

    # ===== EXTREMELY IMPORTANT NOTE =====:
    # Remember that last frequency is not necessary actual frequency, because our wavemeter switching
    # is achieved by manually moving the optical blocker at the beam splitter, so probably the light
    # has long been blocked and have not updated for minutes
    # Another problem is that each set point takes several seconds or even minutes, this means a single
    # measurement at the beginning of the scan could be misleading, we could consider let the frequency
    # monitoring recurring during each scan
    self.set_dataset('last_frequency_422', [0] * self.steps, broadcast=True)
    self.set_dataset('last_frequency_390', [0] * self.steps, broadcast=True)
    self.set_dataset('MCP_voltages',       [0] * 3,          broadcast=True)
    
    self.set_dataset('trapped_signal',     [0] * self.steps, broadcast=True)
    self.set_dataset('loading_signal',     [0] * self.steps, broadcast=True)
    self.set_dataset('lost_signal',        [0] * self.steps, broadcast=True)
    self.set_dataset('ratio_signal',       [0] * self.steps, broadcast=True)
    self.set_dataset('ratio_lost',         [0] * self.steps, broadcast=True)
    
    # counting mode datasets
    self.set_dataset('scan_x',             self.scan_values, broadcast=True)
    self.set_dataset('scan_result',        [0] * self.steps, broadcast=True)
    
    # experiment metadataset
    self.set_dataset('time_cost',          [0] * self.steps, broadcast=True)

    return

#####################################################################
## -3. Analyze  #####################################################
#####################################################################

# 1) Master function for analyze
def my_analyze(self):

    # reset scan value to setting in parameter
    reset_scan_parameter(self)
    close_instruments(self)

    # Save data
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

    name = self.scanning_parameter

    # Get correct value and tool for reseting
    initial_value = next((e['val'] for e in self.config_dict if e.get('par') == name), None)
    #exec(f"import scan_functions._scan_{name} as func")
    #func = globals().get(f"_scan_{name}")
    import scan_functions as sf
    func = getattr(sf, f"_scan_{name}", None)

    # Reset scanning parameter
    func(self, initial_value, [initial_value], scan_check=False)

def close_instruments(self):

    # Close instrument connections created by prepare
    # 1) Close Laser Client
    self.laser.close()
    
    # 2) Close Tickler (DSG821)
    self.tickler.off()
    self.tickler.close()

    # 3) Close RF (RS)
    self.RF_driver.off()
    self.RF_driver.close()
    
    # 4) Close Extraction Pulser (BK4053)
    # Should not turn off ext_pulser because it could kill the AOM
    #self.ext_pulser.off()
    self.ext_pulser.close()
    
    return

