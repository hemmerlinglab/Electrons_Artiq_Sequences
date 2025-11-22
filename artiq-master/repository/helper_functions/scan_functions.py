import time
import numpy as np
import sys

from base_sequences import set_mesh_voltage, set_threshold_voltage, set_multipoles, set_loading_pulse, set_extraction_pulse, set_MCP_voltages, update_detection_time

#####################################################################
##  -- Master Scanning Function  --  ################################
#####################################################################

def scan_parameter(self, my_ind, scan_check = False, reset_value = False):
    """
    scanning any parameter
    easy extension by adding more scanning functions
    removed eval() in the new code
    """

    this_module = sys.modules[__name__]
    param_name = self.scanning_parameter

    # Deal with value reset mode
    if not reset_value:
        val = self.scan_values[my_ind]
    else:
        # reset the value to the one in the parameter listing
        print('Resetting Scanning parameter ...')
        val = getattr(self, param_name)

    # Print feedback when in ordinary mode
    if not scan_check and not reset_value:
        print(f"Scanning parameter {self.scanning_parameter}: {val} ({my_ind+1}/{len(self.scan_values)})")

    # Search for the scanning function dynamically
    scan_func_name = f"_scan_{param_name}"
    func = getattr(this_module, scan_func_name, None)

    if func:
        return func(self, val, self.scan_values, scan_check=scan_check)
    else:
        print(f"Parameter to scan {param_name} has no scanning function yet!")
        return 0

def set_doe_parameters(self, row, ind, steps):
    """
    set multiple parameters for DOE scans
    """

    this_module = sys.modules[__name__]

    print(f"Setting step {ind+1}/{steps} ...")

    for param_name in row.index:
        val = row[param_name]
        scan_func_name = f"_scan_{param_name}"

        func = getattr(this_module, scan_func_name, None)

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

def limit_check(par, scan_values, limits):
    
    check = (np.min(scan_values) >= limits[0]) and (np.max(scan_values) <= limits[1])

    if not check:
        print('Scan range out of bounds for parameter {0}.'.format(par))

    return check

#####################################################################
##  -- Scanning Functions  --  ######################################
#####################################################################
"""
# ---- Temporary Notes ---- #
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

        return limit_check(self.scanning_parameter, scan_values, [0.0, 600.0])
    
    else:
        
        set_mesh_voltage(self, val)
        #time.sleep(3)

        return 1

def _scan_threshold_voltage(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0.0, 10001])

    else:

        set_threshold_voltage(self, val*1e-3)

        return 1

def _scan_MCP_front(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0.0, 700.0])
    
    else:

        self.current_MCP_front = val
        set_MCP_voltages(self, val)

        return 1

# 2. Sequence Parameters  ----------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_load_time(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 10000])
    
    else:
        
        self.load_time = val
        update_detection_time(self)

        set_loading_pulse(self)
        set_extraction_pulse(self)

        return 1

def _scan_wait_time(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 1000000])
    
    else:
        
        self.wait_time = val
        update_detection_time(self)

        set_extraction_pulse(self)

        return 1


# 3. Laser Parameters  -------------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_frequency_422(self, val, scan_values, scan_check = False):

    if scan_check:
        return limit_check(self.scanning_parameter, scan_values, [709.068240, 709.088240])
    
    else:
        
        self.laser.set_frequency(422, val) # It is fine to use 422 or '422' for laserid
        time.sleep(1)
        
        return 1

def _scan_frequency_390(self, val, scan_values, scan_check = False):

    if scan_check:
        return limit_check(self.scanning_parameter, scan_values, [766.100000, 769.600000])
    
    else:

        self.laser.set_frequency(390, val)
        time.sleep(1)
        
        return 1


# 4. Tickling Parameters  ----------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_tickle_frequency(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 1000])
    
    else:
        
        self.tickler.set_freq(val)

        return 1

def _scan_tickle_level(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-30, 20])
    
    else:
        
        self.tickler.set_ampl(val)

        return 1

def _scan_tickle_pulse_length(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [1, 10000])
    
    else:
        
        self.tickle_pulse_length = val

        return 1


# 5. RF Parameters  ----------------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_RF_frequency(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [1.0, 2.4])
    
    else:
        
        self.RF_driver.set_freq(val * 1e9)
        self.spectrum_analyzer.set_center_freq(val * 1e9)

        return 1

def _scan_RF_amplitude(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-30, 11])
    
    else:
        
        self.RF_driver.set_ampl(val)
        self.spectrum_analyzer.set_ref_ampl(min(val+16,18))

        return 1


# 6. Extraction Pulse Parameters  --------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_ext_pulse_length(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [40, 100000])
    
    else:
        
        self.ext_pulse_length = val
        update_detection_time(self)

        set_extraction_pulse(self)

        return 1

def _scan_ext_pulse_level(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0.01, 20])
    
    else:
        
        self.ext_pulse_level = val

        set_extraction_pulse(self)

        return 1


# 6. DC Parameters  ----------------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_U2(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-1.0, +1.0])
    
    else:
        
        self.U2 = val
       
        set_multipoles(self)

        return 1

def _scan_U1(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-2.0, +2.0])
    
    else:
        
        self.U1 = val
       
        set_multipoles(self)

        return 1

def _scan_U4(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.5, +0.5])
    
    else:
        
        self.U4 = val
       
        set_multipoles(self)

        return 1

def _scan_U5(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-2.5, +2.5])
    
    else:
        
        self.U5 = val
       
        set_multipoles(self)

        return 1

def _scan_U3(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.8, +0.8])
    
    else:
        
        self.U3 = val
       
        set_multipoles(self)

        return 1

def _scan_Ex(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-1.0, +1.0])
    
    else:
        
        self.Ex = val
       
        set_multipoles(self)

        return 1

def _scan_Ey(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.2, +0.2])
    
    else:
        
        self.Ey = val
       
        set_multipoles(self)

        return 1

def _scan_Ez(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.8, +0.8])
    
    else:
        
        self.Ez = val
       
        set_multipoles(self)

        return 1
