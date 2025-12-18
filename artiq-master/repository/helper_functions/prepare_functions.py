import numpy as np
import pandas as pd
import datetime
import sys
import os

# instruments within the `drivers` directory
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")
from bk_4053 import BK4053
from rigol   import DSG821
from laser_controller import LaserClient
from RF_controller    import RFController

# something within the same directory
from dc_electrodes import Electrodes
from base_sequences import zotino_initialization, set_multipoles, update_detection_time, set_mesh_voltage, set_threshold_voltage, set_MCP_voltages, set_extraction_pulse, set_loading_pulse
from scan_functions import scan_parameter

# ===================================================================
# 1) Master function for prepare
def ofat_prepare(self):

    prepare_instruments(self)
    prepare_ofat_datasets(self)
    prepare_common_datasets(self)
    prepare_initialization(self)
    prepare_ofat_saving_configuration(self)
    prepare_saving_configuration(self)

def doe_prepare(self):

    prepare_instruments(self)

    # Prepare Datasets
    if self.utility_mode == "DOE Scan":
        prepare_doe_datasets(self)
    elif self.utility_mode == "Single Experiment":
        self.steps = 1
        self.scan_ok = True

    prepare_common_datasets(self)
    prepare_initialization(self)
    prepare_saving_configuration(self)

def optimizer_prepare(self):

    # General Preparations
    prepare_instruments(self)
    prepare_optimizer_datesets(self)
    prepare_common_datasets(self)
    prepare_initialization(self)
    prepare_saving_configuration(self)
    prepare_optimizer_saving_configuration(self)

# ===================================================================
# 2) Subfunctions for prepare
def prepare_instruments(self):

    self.ext_pulser        = BK4053()      # extraction pulse generator and AOM controller
    self.tickler           = DSG821()      # tickle pulse generator
    self.laser             = LaserClient() # Laser Lock GUI client

    # trap drive and measurement
    self.rf = RFController(
        mode = self.RF_amp_mode,
        amplitude = self.RF_amplitude,
        frequency = self.RF_frequency
    )

    # Zotino DC controller
    self.electrodes = Electrodes(trap = self.trap, flipped = self.flip_electrodes)
    for elec in self.electrodes.elec_dict.keys():
        param_name = f"offset_{elec}"
        offset_voltage = getattr(self, param_name)
        self.electrodes.set_offset(elec, offset_voltage)

def prepare_initialization(self):

    # configures the trap drive, mesh voltage, etc ...

    # 1. Laser
    #------------------------------------------------------
    self.laser.set_frequency(390, self.frequency_390)
    self.laser.set_frequency(422, self.frequency_422)

    # 1. RF
    #------------------------------------------------------
    if self.RF_on:
        self.rf.on()
    else:
        self.rf.off()

    # 2. DC voltages
    #------------------------------------------------------
    zotino_initialization(self)
    set_multipoles(self)

    # 3. Mesh, MCP, and Threshold voltage
    #------------------------------------------------------
    #self.mesh = Mesh(initial_voltage = self.mesh_voltage)
    set_mesh_voltage(self, self.mesh_voltage)
    self.current_MCP_front = self.MCP_front
    set_MCP_voltages(self, self.MCP_front)
    set_threshold_voltage(self, self.threshold_voltage*1e-3)

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

def prepare_saving_configuration(self):
    
    # Set the data going to save
    common_data_to_save = [
            {'var' : 'arr_of_timestamps',  'name' : 'array of timestamps during extraction'},
            {'var' : 'last_frequency_422', 'name' : 'array of fetched last frequency from laser lock GUI, actual frequency if the GUI is measuring 422 at the time'},
            {'var' : 'last_frequency_390', 'name' : 'array of fetched last frequency from laser lock GUI, actual frequency if the GUI is measuring 390 at the time'},
            {'var' : 'trapped_signal',     'name' : 'array of trapped electron counts'},
            {'var' : 'loading_signal',     'name' : 'array of loading electron counts'},
            {'var' : 'lost_signal',        'name' : 'array of kicked out electron counts in the first 15us or during the tickle pulse duration when it is smaller than 15us'},
            {'var' : 'ratio_signal',       'name' : 'array of trapped counts / loading counts'},
            {'var' : 'ratio_lost',         'name' : 'array of lost counts / loading counts'},
            {'var' : 'scan_result',        'name' : 'array of recorded counts for counting mode'},
            {'var' : 'time_cost',          'name' : 'array of time cost for each experiment scan'},
            {'var' : 'act_RF_amplitude',   'name' : 'array of actual RF amplitude'}
    ]

    # save sequence file name
    self.data_to_save.extend(common_data_to_save)
    self.config_dict.append({'par' : 'sequence_file', 'val' : self.sequence_filename, 'cmt' : 'Filename of the main sequence file'})

    get_basefilename(self)

    self.core.reset() # Reset the core

    for k in range(1):
        print("")
    print("*"*100)
    print("* Starting new scan")
    print("*"*100)
    print("")

def prepare_ofat_saving_configuration(self):

    self.data_to_save.append({'var' : 'arr_of_setpoints',   'name' : 'array of setpoints'})

    if self.mode == 'Counting':
        self.data_to_save.append({'var' : 'scan_x', 'name' : 'array of setpoints for counting mode, duplicate but in order to be compatible with applet'})

def prepare_optimizer_saving_configuration(self):

    optimizer_data_to_save = [
        {'var' : 'e_trace', 'name' : 'array of electric field trace'},
        {'var' : 'y_best',  'name' : 'array of best signal until now'},
        {'var' : 'ei',      'name' : 'array of expected improvement'}
    ]
    self.data_to_save.extend(optimizer_data_to_save)

def prepare_common_datasets(self):

    update_detection_time(self)

    # timestamps for each sequence iteration
    self.set_dataset('timestamps',         [], broadcast=True)
    
    # data sets to save all time stamps
    self.set_dataset('arr_of_timestamps',  [ [] for _ in range(self.steps) ], broadcast=True)

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
    self.set_dataset('scan_result',        [0] * self.steps, broadcast=True)
    
    # experiment metadataset
    self.set_dataset('time_cost',          [0] * self.steps, broadcast=True)

    # keysight amplitude
    self.set_dataset('act_RF_amplitude', [0] * self.steps, broadcast=True)

def prepare_ofat_datasets(self):

    # Scan interval
    self.scan_values = np.linspace(self.min_scan, self.max_scan, self.steps)

    # Check scan range
    self.scan_ok = scan_parameter(self, 0, scan_check = True)

    # Dataset to store the setpoints
    self.set_dataset('arr_of_setpoints',   self.scan_values, broadcast=True)

    # counting mode datasets
    self.set_dataset('scan_x',             self.scan_values, broadcast=True)

def prepare_doe_datasets(self):

    allowed_params = [x['par'] for x in self.config_dict if x['scanable']]
    self.doe_file = self.doe_file_path + self.doe_file_name
    self.setpoints, self.fields_to_fill, self.steps = \
        load_doe_setpoints(self.doe_file, allowed_params)

    # Safety: perform scan check for all parameters
    self.scan_ok = True
    for param_to_scan in self.setpoints.columns:
        self.scan_values = self.setpoints[param_to_scan].to_numpy()
        self.scanning_parameter = param_to_scan
        self.scan_ok = self.scan_ok and scan_parameter(self, 0, scan_check = True)

    # To let `arr_or_setpoints` and `scan_x` based applet to run
    xaxis = np.arange(self.steps)
    self.set_dataset('arr_of_setpoints', xaxis, broadcast=True)
    self.set_dataset('scan_x',           xaxis, broadcast=True)

def prepare_optimizer_datesets(self):

    # For compatibility with preparing other datasets
    self.steps = self.max_iteration + self.init_sample_size
    self.E_sampled = []
    self.y_sampled = []

    # Bounds matrix
    self.bounds = np.array([
        [self.min_Ex, self.max_Ex],
        [self.min_Ey, self.max_Ey],
        [self.min_Ez, self.max_Ez]
    ])

    # Datasets for optimizer
    xaxis = np.arange(self.steps, dtype=float)
    self.set_dataset("arr_of_setpoints", xaxis, broadcast=True)
    self.set_dataset("e_trace", [np.zeros(3) for _ in range(self.steps)], broadcast=True)
    self.set_dataset("y_best", [0] * self.max_iteration, broadcast=True)
    self.set_dataset("ei", [0] * self.max_iteration, broadcast=True)
    self.set_dataset("length_scale", [0] * self.max_iteration, broadcast=True)
    self.set_dataset("best_rel_noise", [0] * self.max_iteration, broadcast=True)
    self.set_dataset("optimizer_x", list(range(self.max_iteration)), broadcast=True)

    self.scan_ok = True

# ===================================================================
# 3) Helper Functions
def load_doe_setpoints(file_path, allowed_params):

    full_table = pd.read_csv(file_path)

    # We do not use `Run Order`, we use the sequence of csv file
    if "Run Order" in full_table.columns:
        full_table = full_table.drop(columns=["Run Order"])

    setpoint_columns = []
    response_columns = []

    # Identify setpoin columns and data columns
    for col_name in full_table.columns:
        if full_table[col_name].isna().all():
            response_columns.append(col_name)
        else:
            setpoint_columns.append(col_name)

    # To check if the setpoint columns are legal parameters
    for col_name in setpoint_columns:
        if col_name not in allowed_params:
            raise ValueError(f"Column '{col_name}' is not in allowed_params!")

    setpoints = full_table[setpoint_columns]
    
    return setpoints, response_columns, len(setpoints)

def get_basefilename(self, extension = ''):
    my_timestamp = datetime.datetime.today()

    self.today = datetime.datetime.today()
    self.today = self.today.strftime('%Y%m%d')

    self.datafolder = '/home/electrons/software/data/'

    basefolder = str(self.today) # 20220707
    # create new folder if doesn't exist yet
    if not os.path.exists(self.datafolder + basefolder):
        os.makedirs(self.datafolder + basefolder)

    self.scan_timestamp = str(my_timestamp.strftime('%Y%m%d_%H%M%S'))

    self.basefilename = self.datafolder + basefolder + '/' + self.scan_timestamp # 20220707_150655
