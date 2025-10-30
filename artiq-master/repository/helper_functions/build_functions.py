from artiq.experiment import *

list_of_traps = ["Single PCB", "UCB 3 PCB"]

# ===================================================================
# - Set Attribute with Config Saving

def my_setattr(self, arg, val, scanable = True):
    
    # define the attribute
    self.setattr_argument(arg, val)

    # add each attribute to the config dictionary
    if hasattr(val, 'unit'):
        exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'unit' : '" + str(val.unit) + "', 'scanable' : " + str(scanable) + "})")
    else:
        exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'scanable' : " + str(scanable) + "})")

    return

# ===================================================================
# - Build Functions

# 1) Master function for build
def ofat_build(self):

    load_variables(self)
    load_attributes(self)
    load_common_parameters(self)
    load_ofat_parameters(self) # Keep scanning setups at the end

    return

def doe_build(self):

    load_variables(self)
    load_attributes(self)
    load_doe_parameters(self)  # Keep doe setups at the top
    load_common_parameters(self)

    return

# 2) Subfunctions for build
def load_variables(self):

    self.config_dict = []
    self.wavemeter_frequencies = []
    self.data_to_save = []

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

def load_common_parameters(self):

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

    return

def load_ofat_parameters(self):

    # OFAT Scan Settings
    #------------------------------------------------------
    list_of_parameters = [x['par'] for x in self.config_dict if x['scanable']]
    my_setattr(self, 'scanning_parameter', EnumerationValue(list_of_parameters, default = list_of_parameters[0]))
    my_setattr(self, 'min_scan',           NumberValue(default=100,unit='',scale=1,ndecimals=6,step=.000001))
    my_setattr(self, 'max_scan',           NumberValue(default=200,unit='',scale=1,ndecimals=6,step=.000001))
    my_setattr(self, 'steps',              NumberValue(default=100,unit='steps to scan',scale=1,ndecimals=0,step=1))

    return

def load_doe_parameters(self):

    # DOE Scan Settings
    #------------------------------------------------------
    my_setattr(self, 'utility_mode',  EnumerationValue(['Single Parameter Scan', 'DOE Scan'], default='DOE Scan'), scanable=False)
    my_setattr(self, 'doe_file_path', StringValue(default='/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/DOE_configs/doe_table.csv'), scanable=False)

    return