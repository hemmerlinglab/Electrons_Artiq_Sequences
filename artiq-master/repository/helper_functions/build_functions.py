from artiq.experiment import NumberValue, EnumerationValue, BooleanValue, StringValue
from traps import traps

MODES_LIST = ["Lifetime", "Lifetime_fast", "Trapping", "Counting"]

# ===================================================================
# - Set Attribute with Config Saving

def my_setattr(self, arg, val, group=None, scanable = True):

    # define the attribute
    self.setattr_argument(arg, val, group=group)

    # get current attribute value from artiq object
    current_val = getattr(self, arg)

    # create config_dict entry
    entry = {"par": arg, "val": current_val, "scanable": scanable}
    if hasattr(val, "unit"): entry["unit"] = str(val.unit)

    # append the entry to config dict
    self.config_dict.append(entry)

# ===================================================================
# - Build Functions

# 1) Master function for build
def ofat_build(self):

    load_variables(self)
    load_attributes(self)
    
    # Load Parameters
    my_setattr(self, 'mode', EnumerationValue(MODES_LIST, default='Trapping'), scanable = False)
    load_common_parameters(self)       # Parameters used in all sequences
    load_experiment_parameters(self)   # Not used in find_optimal_E
    load_ofat_parameters(self)         # Scanning setups at the bottom (have to be so due to the logic of `list of parameters`)

def doe_build(self):

    load_variables(self)
    load_attributes(self)

    # Load Parameters
    my_setattr(self, 'mode', EnumerationValue(MODES_LIST, default='Trapping'), scanable = False)
    load_doe_parameters(self)          # Keep doe setups at the top
    load_common_parameters(self)       # Parameters used in all sequences
    load_experiment_parameters(self)   # Not used in find_optimal_E

def optimizer_build(self):

    load_variables(self)
    load_attributes(self)

    # Load Parameters
    load_common_parameters(self)
    load_optimizer_parameters(self)


# 2) Subfunctions for build
def load_variables(self):

    self.config_dict = []
    self.err_list = []
    self.wavemeter_frequencies = []
    self.data_to_save = []

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

def load_common_parameters(self):

    # 1. Display Settings (histogram_on is impacting experiment sequence)
    #------------------------------------------------------
    group_display = "Display Settings"
    my_setattr(self, 'histogram_on',      BooleanValue(default=True), group=group_display, scanable=False)
    my_setattr(self, 'bin_width',         NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1), group=group_display, scanable = False)
    my_setattr(self, 'histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1), group=group_display, scanable = False)

    # 2. Detector Settings
    #------------------------------------------------------
    group_detector = "Detector Settings"
    my_setattr(self, 'mesh_voltage',      NumberValue(default=120,unit='V',scale=1,ndecimals=0,step=1), group=group_detector)
    my_setattr(self, 'MCP_front',         NumberValue(default=400,unit='V',scale=1,ndecimals=0,step=1), group=group_detector)
    my_setattr(self, 'threshold_voltage', NumberValue(default=100,unit='mV',scale=1,ndecimals=0,step=1), group=group_detector)

    # 3. Sequence Settings
    #------------------------------------------------------
    # 3-1) General
    group_general = "Sequence Settings (Trapping & Lifetime Mode)"
    my_setattr(self, 'load_time',         NumberValue(default=210,unit='us',scale=1,ndecimals=0,step=1), group=group_general)

    # 3-1) Trapping Mode
    group_trapping = "Sequence Settings (Trapping Mode)"
    my_setattr(self, 'wait_time',         NumberValue(default=90,unit='us',scale=1,ndecimals=0,step=1), group=group_trapping)
    my_setattr(self, 'no_of_repeats',     NumberValue(default=10000,unit='',scale=1,ndecimals=0,step=1), group=group_trapping)

    # 3-2) Counting Mode
    group_counting = "Sequence Settings (Counting Mode)"
    my_setattr(self, 'detection_time',    NumberValue(default=1000,unit='ms for counting mode only',scale=1,ndecimals=0,step=1), group=group_counting)

    # 3-3) Lifetime Mode
    group_lifetime = "Sequence_Settings (Lifetime Mode)"
    my_setattr(self, 'wait_times_path',   StringValue(default='/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions/Table/'), group=group_lifetime, scanable=False)
    my_setattr(self, 'wait_times_file',   StringValue(default='lifetime_wait_times_short.csv'), group=group_lifetime, scanable=False)
    my_setattr(self, 'repeats_ratio',     NumberValue(default=1.0,unit='',scale=1,ndecimals=2,step=0.01), group=group_lifetime)
    my_setattr(self, 'wait_time_fast',    NumberValue(default=700,unit='us',scale=1,ndecimals=0,step=1), group=group_lifetime)

    # 4. Trap Settings
    #------------------------------------------------------
    self.trap = "Single PCB"
    self.flip_electrodes = False

    # 5. Laser Settings
    #------------------------------------------------------
    group_laser = "Laser Settings"
    my_setattr(self, 'frequency_422',     NumberValue(default=709.076990,unit='THz',scale=1,ndecimals=6,step=1e-6), group=group_laser)
    my_setattr(self, 'frequency_390',     NumberValue(default=768.708843,unit='THz',scale=1,ndecimals=6,step=1e-6), group=group_laser)
    my_setattr(self, 'laser_failure',     EnumerationValue(['wait for fix', 'raise error'], default='wait for fix'), group=group_laser, scanable=False)

    # 6. RF Settings
    #------------------------------------------------------
    group_RF = "RF Drive Settings"
    my_setattr(self, 'RF_on',             BooleanValue(default=False), group=group_RF)
    my_setattr(self, 'RF_amp_mode',       EnumerationValue(['setpoint', 'actual', 'locked'], default='setpoint'), group=group_RF, scanable=False)
    my_setattr(self, 'RF_amplitude',      NumberValue(default=4,unit='dBm',scale=1,ndecimals=2,step=.01), group=group_RF)
    my_setattr(self, 'RF_frequency',      NumberValue(default=1.732,unit='GHz',scale=1,ndecimals=4,step=.0001), group=group_RF)

    # 7. Extraction Pulse Settings
    #------------------------------------------------------
    group_ext = "Extraction Pulse Settings"
    my_setattr(self, 'ext_pulse_length',  NumberValue(default=900,unit='ns',scale=1,ndecimals=0,step=1), group=group_ext)
    my_setattr(self, 'ext_pulse_level',   NumberValue(default=15,unit='V',scale=1,ndecimals=2,step=.01), group=group_ext)

    # 8. DC Settings - 2nd Order Multipoles
    #------------------------------------------------------
    group_DC = "DC Multipoles Settings"
    my_setattr(self, 'U1',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)
    my_setattr(self, 'U2',                NumberValue(default=-0.22,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)
    my_setattr(self, 'U3',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)
    my_setattr(self, 'U4',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)
    my_setattr(self, 'U5',                NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)

def load_experiment_parameters(self):

    # 1. 1st Order Multipoles
    #------------------------------------------------------
    group_DC = "DC Multipoles Settings"
    my_setattr(self, 'Ex',                  NumberValue(default=-0.199,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)
    my_setattr(self, 'Ey',                  NumberValue(default=0.051,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)
    my_setattr(self, 'Ez',                  NumberValue(default=-0.047,unit='V',scale=1,ndecimals=3,step=.001), group=group_DC)

    # 2. Tickle Settings
    #------------------------------------------------------
    group_tickling = "Tickling Settings"
    my_setattr(self, 'tickle_on',           BooleanValue(default=False), group=group_tickling, scanable = False)
    my_setattr(self, 'tickle_level',        NumberValue(default=-10,unit='dBm',scale=1,ndecimals=1,step=1), group=group_tickling)
    my_setattr(self, 'tickle_frequency',    NumberValue(default=64,unit='MHz',scale=1,ndecimals=4,step=.0001), group=group_tickling)
    my_setattr(self, 'tickle_pulse_length', NumberValue(default=80,unit='us',scale=1,ndecimals=1,step=1), group=group_tickling)

    # 3. DC Offset Settings
    #------------------------------------------------------
    group_offset = "DC Offset Settings"
    if not self.flip_electrodes: trap_key = self.trap
    else: trap_key = self.trap + " Flipped"
    list_of_electrodes = traps[trap_key]["electrodes_order"]
    for elec in list_of_electrodes:
        param_name = f"offset_{elec}"
        my_setattr(self, param_name,        NumberValue(default=0.0,unit='V',scale=1,ndecimals=2,step=0.01), group=group_offset)

def load_ofat_parameters(self):

    # OFAT Scan Settings
    #------------------------------------------------------
    list_of_parameters = [x['par'] for x in self.config_dict if x['scanable']]
    my_setattr(self, 'scanning_parameter', EnumerationValue(list_of_parameters, default = list_of_parameters[0]), scanable=False)
    my_setattr(self, 'min_scan',           NumberValue(default=100,unit='',scale=1,ndecimals=6,step=.000001), scanable=False)
    my_setattr(self, 'max_scan',           NumberValue(default=200,unit='',scale=1,ndecimals=6,step=.000001), scanable=False)
    my_setattr(self, 'steps',              NumberValue(default=100,unit='steps to scan',scale=1,ndecimals=0,step=1), scanable=False)

def load_doe_parameters(self):

    # DOE Scan Settings
    #------------------------------------------------------
    my_setattr(self, 'utility_mode',  EnumerationValue(['Single Experiment', 'DOE Scan'], default='DOE Scan'), scanable=False)
    my_setattr(self, 'doe_file_path', StringValue(default='/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/doe_configs/'), scanable=False)
    my_setattr(self, 'doe_file_name', StringValue(default='doe_table.csv'), scanable=False)

def load_optimizer_parameters(self):

    optimization_targets = ['trapped_signal', 'ratio_signal', 'ratio_weighted', 'lost_signal', 'ratio_lost', 'loading_signal']

    group_bound = "Boundry Settings"
    group_algorithm = "Optimizer Settings"
    group_advanced = "Advanced Settings"

    # Optimizer Settings
    #------------------------------------------------------
    my_setattr(self, 'optimize_target', EnumerationValue(optimization_targets, default=optimization_targets[0]), scanable=False) # Which signal to optimize
    my_setattr(self, 'max_iteration',   NumberValue(default=50,unit='',scale=1,ndecimals=0,step=1), group=group_algorithm, scanable=False)
    my_setattr(self, 'tolerance',       NumberValue(default=5e-3,unit='',scale=1,ndecimals=6,step=1e-6), group=group_algorithm, scanable=False)
    my_setattr(self, 'converge_count',  NumberValue(default=3,unit='',scale=1,ndecimals=0,step=1), group=group_algorithm, scanable=False)
    my_setattr(self, 'min_Ex',          NumberValue(default=-0.3,unit='',scale=1,ndecimals=3,step=.001), group=group_bound, scanable=False)
    my_setattr(self, 'max_Ex',          NumberValue(default=0.05,unit='',scale=1,ndecimals=3,step=.001), group=group_bound, scanable=False)
    my_setattr(self, 'min_Ey',          NumberValue(default=-0.05,unit='',scale=1,ndecimals=3,step=.001), group=group_bound, scanable=False)
    my_setattr(self, 'max_Ey',          NumberValue(default=0.2,unit='',scale=1,ndecimals=3,step=.001), group=group_bound, scanable=False)
    my_setattr(self, 'min_Ez',          NumberValue(default=-0.1,unit='',scale=1,ndecimals=3,step=.001), group=group_bound, scanable=False)
    my_setattr(self, 'max_Ez',          NumberValue(default=0.1,unit='',scale=1,ndecimals=3,step=.001), group=group_bound, scanable=False)
    my_setattr(self, 'min_iteration',   NumberValue(default=5,unit='',scale=1,ndecimals=0,step=1), group=group_advanced, scanable=False)
    my_setattr(self, 'n_candidate_run', NumberValue(default=1024,unit='',scale=1,ndecimals=0,step=1), group=group_advanced, scanable=False)
    my_setattr(self, 'n_candidate_anal',NumberValue(default=4096,unit='',scale=1,ndecimals=0,step=1), group=group_advanced, scanable=False)
    my_setattr(self, 'init_sample_size',NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1), group=group_advanced, scanable=False)

    # For compatibility
    self.mode = "Trapping"
    self.Ex, self.Ey, self.Ez = (0.0, 0.0, 0.0)
    self.tickle_on = False
    self.tickle_pulse_length = 80
    self.tickle_level = -10

    if not self.flip_electrodes: trap_key = self.trap
    else: trap_key = self.trap + " Flipped"
    list_of_electrodes = traps[trap_key]["electrodes_order"]
    for elec in list_of_electrodes:
        param_name = f"offset_{elec}"
        setattr(self, param_name, 0.0)

