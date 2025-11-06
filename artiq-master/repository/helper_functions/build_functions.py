from artiq.experiment import NumberValue, EnumerationValue, BooleanValue, StringValue

list_of_traps = ["Single PCB", "UCB 3 PCB"]

# ===================================================================
# - Set Attribute with Config Saving

def my_setattr(self, arg, val, scanable = True):

    # define the attribute
    self.setattr_argument(arg, val)

    # get current attribute value from artiq object
    current_val = getattr(self, arg)

    # create config_dict entry
    entry = {"par": arg, "val": current_val, "scanable": str(scanable)}
    if hasattr(val, "unit"): entry["unit"] = str(val.unit)

    # append the entry to config dict
    self.config_dict.append(entry)

    return

# ===================================================================
# - Build Functions

# 1) Master function for build
def ofat_build(self):

    load_variables(self)
    load_attributes(self)
    
    # Load Parameters
    my_setattr(self, 'mode', EnumerationValue(['Trapping', 'Counting'],default='Trapping'), scanable = False)
    load_common_parameters(self)     # Parameters used in all sequences
    load_experiment_parameters(self)   # Not used in find_optimal_E
    load_ofat_parameters(self)       # Keep scanning setups at the end

    return

def doe_build(self):

    load_variables(self)
    load_attributes(self)

    # Load Parameters
    my_setattr(self, 'mode', EnumerationValue(['Trapping', 'Counting'],default='Trapping'), scanable = False)
    load_doe_parameters(self)        # Keep doe setups at the top
    load_common_parameters(self)     # Parameters used in all sequences
    load_experiment_parameters(self)   # Not used in find_optimal_E

    return

def optimizer_build(self):

    load_variables(self)
    load_attributes(self)

    # Load Parameters
    load_optimizer_parameters(self)
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

    # 1. Display Settings (histogram_on is impacting experiment sequence)
    #------------------------------------------------------
    my_setattr(self, 'histogram_on',      BooleanValue(default=True), scanable=False)
    my_setattr(self, 'bin_width',         NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1), scanable = False)
    my_setattr(self, 'histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1), scanable = False)

    # 2. Detector Settings
    #------------------------------------------------------
    my_setattr(self, 'mesh_voltage',      NumberValue(default=120,unit='V',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'MCP_front',         NumberValue(default=400,unit='V',scale=1,ndecimals=0,step=1))

    # 3. Sequence Settings
    #------------------------------------------------------
    my_setattr(self, 'wait_time',         NumberValue(default=90,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'load_time',         NumberValue(default=210,unit='us',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'no_of_repeats',     NumberValue(default=10000,unit='',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'detection_time',    NumberValue(default=1000,unit='ms for counting mode only',scale=1,ndecimals=0,step=1))

    # 4. Trap Settings
    #------------------------------------------------------
    my_setattr(self, 'trap',              EnumerationValue(list_of_traps,default=list_of_traps[0]), scanable = False)
    my_setattr(self, 'flip_electrodes',   BooleanValue(default=False))

    # 5. Laser Settings
    #------------------------------------------------------
    my_setattr(self, 'frequency_422',     NumberValue(default=709.078300,unit='THz',scale=1,ndecimals=6,step=1e-6))
    my_setattr(self, 'frequency_390',     NumberValue(default=768.708843,unit='THz',scale=1,ndecimals=6,step=1e-6))

    # 6. RF Settings
    #------------------------------------------------------
    my_setattr(self, 'RF_on',             BooleanValue(default=False))
    my_setattr(self, 'RF_amplitude',      NumberValue(default=4,unit='dBm',scale=1,ndecimals=1,step=.1))
    my_setattr(self, 'RF_frequency',      NumberValue(default=1.732,unit='GHz',scale=1,ndecimals=4,step=.0001))

    # 7. Extraction Pulse Settings
    #------------------------------------------------------
    my_setattr(self, 'ext_pulse_length',  NumberValue(default=900,unit='ns',scale=1,ndecimals=0,step=1))
    my_setattr(self, 'ext_pulse_level',   NumberValue(default=15,unit='V',scale=1,ndecimals=2,step=.01))

    # 8. DC Settings - 2nd Order Multipoles
    #------------------------------------------------------
    my_setattr(self, 'U1',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U2',                NumberValue(default=-0.13,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U3',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U4',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'U5',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))

    return

def load_experiment_parameters(self):

    # 1. 1st Order Multipoles
    #------------------------------------------------------
    my_setattr(self, 'Ex',                  NumberValue(default=-0.15,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'Ey',                  NumberValue(default=0.14,unit='V',scale=1,ndecimals=3,step=.001))
    my_setattr(self, 'Ez',                  NumberValue(default=0,unit='V',scale=1,ndecimals=3,step=.001))

    # 2. Tickle Settings
    #------------------------------------------------------
    my_setattr(self, 'tickle_on',           BooleanValue(default=False), scanable = False)
    my_setattr(self, 'tickle_level',        NumberValue(default=-10,unit='dBm',scale=1,ndecimals=1,step=1))
    my_setattr(self, 'tickle_frequency',    NumberValue(default=64,unit='MHz',scale=1,ndecimals=4,step=.0001))
    my_setattr(self, 'tickle_pulse_length', NumberValue(default=80,unit='us',scale=1,ndecimals=1,step=1))

    return

def load_ofat_parameters(self):

    # OFAT Scan Settings
    #------------------------------------------------------
    list_of_parameters = [x['par'] for x in self.config_dict if x['scanable']]
    my_setattr(self, 'scanning_parameter', EnumerationValue(list_of_parameters, default = list_of_parameters[0]), scanable=False)
    my_setattr(self, 'min_scan',           NumberValue(default=100,unit='',scale=1,ndecimals=6,step=.000001), scanable=False)
    my_setattr(self, 'max_scan',           NumberValue(default=200,unit='',scale=1,ndecimals=6,step=.000001), scanable=False)
    my_setattr(self, 'steps',              NumberValue(default=100,unit='steps to scan',scale=1,ndecimals=0,step=1), scanable=False)

    return

def load_doe_parameters(self):

    # DOE Scan Settings
    #------------------------------------------------------
    my_setattr(self, 'utility_mode',  EnumerationValue(['Single Experiment', 'DOE Scan'], default='DOE Scan'), scanable=False)
    my_setattr(self, 'doe_file_path', StringValue(default='/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/doe_configs/'), scanable=False)
    my_setattr(self, 'doe_file_name', StringValue(default='doe_table.csv'), scanable=False)

    return

def load_optimizer_parameters(self):

    optimization_targets = ['trapped_signal', 'ratio_signal', 'lost_signal', 'ratio_lost', 'loading_signal']
    methods = ['central', 'forward']

    # Optimizer Settings
    #------------------------------------------------------
    my_setattr(self, 'optimize_target', EnumerationValue(optimization_targets, default=optimization_targets[0]), scanable=False) # Which signal to optimize
    my_setattr(self, 'method',          EnumerationValue(methods, default=methods[0]), scanable=False)                           # Which method to evaluate derivatives
    my_setattr(self, 'initial_Ex',      NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=.001), scanable=False)          # First guess on Ex
    my_setattr(self, 'initial_Ey',      NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=.001), scanable=False)          # First guess on Ey
    my_setattr(self, 'initial_Ez',      NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=.001), scanable=False)          # First guess on Ez
    my_setattr(self, 'max_iteration',   NumberValue(default=30,unit='',scale=1,ndecimals=0,step=1), scanable=False)              # Max number of iteration allowed
    my_setattr(self, 'diff_step',       NumberValue(default=0.02,unit='',scale=1,ndecimals=3,step=.001), scanable=False)         # Stepsize to evaluate gradients
    my_setattr(self, 'alpha0',          NumberValue(default=0.05,unit='',scale=1,ndecimals=3,step=.001), scanable=False)         # Standard stepsize to move
    my_setattr(self, 'grad_rtol',       NumberValue(default=1e-3,unit='',scale=1,ndecimals=8,step=1e-8), scanable=False)         # Convergence criteria 1: gradient_norm <= rtol * center_value + atol
    my_setattr(self, 'grad_atol',       NumberValue(default=1e-5,unit='',scale=1,ndecimals=10,step=1e-10), scanable=False)       # Convergence criteria 1: gradient_norm <= rtol * center_value + atol
    my_setattr(self, 'min_step',        NumberValue(default=5e-3,unit='',scale=1,ndecimals=3,step=.001), scanable=False)         # Convergence criteria 2: |E_new - E_curr| <= min_step
    my_setattr(self, '')

    return