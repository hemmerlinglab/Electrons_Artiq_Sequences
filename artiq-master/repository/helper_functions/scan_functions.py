import time
import numpy as np
import sys

from base_sequences import set_mesh_voltage, set_threshold_voltage, set_multipoles, set_loading_pulse, set_extraction_pulse, set_MCP_voltages, update_detection_time

#####################################################################
##  -- Master Scanning Functions  --  ###############################
#####################################################################

def scan_parameter(self, my_ind, scan_check = False, reset_value = False):
    """
    scanning any parameter
    easy extension by adding more scanning functions
    removed eval() in the new code
    """

    param_name = self.scanning_parameter

    # Deal with value reset mode
    if not reset_value:
        val = self.scan_values[my_ind]
    else:
        # reset the value to the one in the parameter listing
        print('Resetting Scanning parameter ...')
        for entry in self.config_dict:
            if entry["par"] == param_name:
                val = entry["val"]
                break

    # Print feedback when in ordinary mode
    if not scan_check and not reset_value:
        print(f"Scanning parameter {self.scanning_parameter}: {val} ({my_ind+1}/{len(self.scan_values)})")

    # Search for the scanning function dynamically
    func = _get_scan_function(param_name)

    if func:
        return func(self, val, self.scan_values, scan_check=scan_check)
    else:
        print(f"Parameter to scan {param_name} has no scanning function yet!")
        return 0

def set_doe_parameters(self, row, ind, steps):
    """
    set multiple parameters for DOE scans
    """

    print(f"Setting step {ind+1}/{steps} ...")

    for param_name in row.index:
        val = row[param_name]

        func = _get_scan_function(param_name)

        if func:
            func(self, val, [val], scan_check=False)
            print(f"    Set {param_name} = {val}")
        else:
            print(f"Parameter {param_name} has no scanning function yet!")
            return 0

    return 1

#####################################################################
##  -- Utility Function  --  ########################################
#####################################################################

def _limit_check(par, scan_values, limits):
    
    check = (np.min(scan_values) >= limits[0]) and (np.max(scan_values) <= limits[1])
    if not check:
        print('Scan range out of bounds for parameter {0}.'.format(par))

    return check

def _get_scan_function(param_name):
    """
    Search for scan function of scanable parameter
    1. If parameter name starts with "offset_", generate with `_create_offset_scanner`
    2. If parameter is a DC multipole, generate with `_create_multipole_scanner`
    3. Otherwise, search for function named `_scan_{param_name}`
    """

    multipole_list = ["Ex", "Ey", "Ez", "U1", "U2", "U3", "U4", "U5"]

    if param_name.startswith("offset_"):
        elec_name = param_name.replace("offset_", "")
        return _create_offset_scanner(elec_name)
    elif param_name in multipole_list:
        return _create_multipole_scanner(param_name)
    else:
        this_module = sys.modules[__name__]
        scan_func_name = f"_scan_{param_name}"
        return getattr(this_module, scan_func_name, None)

#####################################################################
##  -- Scanning Functions  --  ######################################
#####################################################################
"""
# ---- General Notes ---- #
To build scanning functions:
1. make sure function name matches f"_scan_{parameter_name}"
2. The function must take 4 parameters:
  - `self`: To work with ArtiQ Experiment classes
  - `val`: Input for ordinary mode
  - `scan_values`: Input for scan check mode
  - `scan_check`: Mode tuner, default `False`
3. The function must have two modes, controlled by `scan_check`:
  - Ordinary Mode: To scan the parameter
  - Scan Check Mode: To check if the scanning range works
"""
# 1. Detector Parameters  ----------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_mesh_voltage(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0.0, 600.0])
    
    else:
        #self.mesh.set_voltage(val)
        set_mesh_voltage(self, val)
        #time.sleep(3)

        return 1

def _scan_threshold_voltage(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0.0, 10001])

    else:
        set_threshold_voltage(self, val*1e-3)

        return 1

def _scan_MCP_front(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0.0, 700.0])
    
    else:
        self.current_MCP_front = val
        set_MCP_voltages(self, val)

        return 1

# 2. Sequence Parameters  ----------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_load_time(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0, 10000])
    
    else:
        self.load_time = val
        update_detection_time(self)
        set_loading_pulse(self)
        set_extraction_pulse(self)

        return 1

def _scan_wait_time(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0, 1000000])
    
    else:
        self.wait_time = val
        update_detection_time(self)
        set_extraction_pulse(self)

        return 1

def _scan_no_of_repeats(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0, 10000000])
    
    else:
        self.no_of_repeats = val

        return 1

# 3. Laser Parameters  -------------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_frequency_422(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [709.068240, 709.088240])
    
    else:
        self.laser.set_frequency(422, val) # It is fine to use 422 or '422' for laserid
        time.sleep(1)
        
        return 1

def _scan_frequency_390(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [766.100000, 769.600000])
    
    else:
        self.laser.set_frequency(390, val)
        time.sleep(1)
        
        return 1


# 4. Tickling Parameters  ----------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_tickle_frequency(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0, 1000])
    
    else:
        self.tickler.set_freq(val)

        return 1

def _scan_tickle_level(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [-30, 20])
    
    else:
        self.tickler.set_ampl(val)

        return 1

def _scan_tickle_pulse_length(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [1, 10000])
    
    else:
        self.tickle_pulse_length = val

        return 1


# 5. RF Parameters  ----------------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_RF_frequency(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [1.0, 2.4])
    
    else:
        self.rf.set_frequency(val * 1e9)

        return 1

def _scan_RF_amplitude(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [-30, 11])
    
    else:
        self.rf.set_amplitude(val)

        return 1


# 6. Extraction Pulse Parameters  --------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_ext_pulse_length(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [40, 100000])
    
    else:
        
        self.ext_pulse_length = val
        update_detection_time(self)
        set_extraction_pulse(self)

        return 1

def _scan_ext_pulse_level(self, val, scan_values, scan_check = False):

    if scan_check:
        return _limit_check(self.scanning_parameter, scan_values, [0.01, 20])
    
    else:  
        self.ext_pulse_level = val
        set_extraction_pulse(self)

        return 1


# 6. DC Parameters (Handled by function factory) -----------------------------#
#-----------------------------------------------------------------------------#
def _create_multipole_scanner(multipole_name):
    """
    Create functions that can be used to scan DC multipoles
    [Ex, Ey, Ez, U1, U2, U3, U4, U5]
    """

    def _scanner(self, val, scan_values, scan_check = False):

        # Safety check has been done by `Electrode` class, so just pass there
        if scan_check:
            return 1

        else:
            # set_multipoles relies on self attributes, so we have to modify here
            setattr(self, multipole_name, val)
            set_multipoles(self)
            return 1
 
    return _scanner

def _create_offset_scanner(elec_name):
    """
    Create functions that can be used to scan DC offsets
    electrode names defined by traps.py
    """

    def _scanner(self, val, scan_values, scan_check = False):

        # Safety check has been done by `Electrode` class, so just pass there
        if scan_check:
            return 1

        else:
            self.electrodes.set_offset(elec_name, val)
            set_multipoles(self)
            return 1

    return _scanner
