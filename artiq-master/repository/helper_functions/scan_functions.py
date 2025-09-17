import time
import numpy as np
import time

from base_sequences import set_mesh_voltage, set_multipoles, set_loading_pulse, set_extraction_pulse, set_MCP_voltages, update_detection_time

#####################################################################
##  -- Master Scanning Function  --  ################################
#####################################################################

def scan_parameter(self, my_ind, scan_check = False, reset_value = False):
    """
    scanning any parameter
    easy extension by adding more scanning functions
    """
    
    # Deal with value reset mode
    if not reset_value:
        val = self.scan_values[my_ind]
    else:
        # reset the value to the one in the parameter listing
        print('Reseting Scanning parameter ...')
        val = eval('self.' + self.scanning_parameter)

    # Print feedback when in ordinary mode
    if not scan_check and not reset_value:
        print("Scanning parameter {3}: {2} ({0}/{1})".format(my_ind, len(self.scan_values), val, self.scanning_parameter))\

    # Check if scanning function exist and call
    if self.scanning_parameter in ['mesh_voltage', 'MCP_front', 'frequency_422', 'frequency_390', 'RF_frequency', 'RF_amplitude', 'tickle_frequency', 'tickle_level', 'tickle_pulse_length', 'load_time', 'wait_time', 'ext_pulse_length', 'ext_pulse_amplitude', 'U1', 'U2', 'U3', 'U4', 'U5', 'Ex', 'Ey', 'Ez']:
        return eval('_scan_' + self.scanning_parameter + '(self, val, self.scan_values, scan_check = scan_check)')

    else:
        print('Parameter to scan {0} has no scanning function yet'.format(self.scanning_parameter))
        return 0

    return 

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

How scanning functions work?
1. In prepare stage:
  - In `general_scan.py`, `prepare` calls `my_prepare` in `base_functions.py`
  - In `base_functions.py`, `my_prepare` calls `prepare_datasets`, then 
    `prepare_datasets` calls `scan_parameter` in scan check mode
  - `scan_parameter` calls target function in scan check mode to get feedback
    about scanning range
2. In run stage:
  - `general_scan.py` calls `scan_parameter` in the main loop in `run`
  - `scan_parameter` function calls target function in ordinary mode to set
    target parameter to current value
3. In analyze stage:
  - In `general_scan.py`, `analyze` calls `my_analyze` in `base_functions.py`
  - In `base_functions.py`, `my_analyze` calls `reset_scan_parameter`, then 
    `reset_scan_parameter` calls correct scan function to reset the value.
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

def _scan_MCP_front(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0.0, 700.0])
    
    else:
        
        if val > self.current_MCP_front:
            val_steps = np.arange(self.current_MCP_front, val, 50)
            for v in val_steps[1:]:
                print('Setting MCP front to: '  + str(v) + 'V (Intermediate steps)')
                set_MCP_voltages(self, v)
                time.sleep(15)
            print('Setting MCP front to: ' + str(val) + 'V\n')
            self.current_MCP_front = val
            set_MCP_voltages(self, val)
            time.sleep(5)

        else:
            val_steps = np.arange(self.current_MCP_front, val, -50)
            for v in val_steps[1:]:
                print('Setting MCP front to: ' + str(v) + 'V (Intermediate steps)')
                set_MCP_voltages(self, v)
                time.sleep(5)
            print('Setting MCP front to: ' + str(val) + 'V\n')
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

        return limit_check(self.scanning_parameter, scan_values, [0, 10000])
    
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
        
        self.tickler.set_level(val)

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

        return limit_check(self.scanning_parameter, scan_values, [1.5, 1.7])
    
    else:
        
        self.RF_driver.set_freq(val * 1e9)

        return 1

def _scan_RF_amplitude(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-30, 8])
    
    else:
        
        self.RF_driver.set_ampl(val)

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

def _scan_ext_pulse_amplitude(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0.01, 20])
    
    else:
        
        self.ext_pulse_amplitude = val

        set_extraction_pulse(self)

        return 1


# 6. DC Parameters  ----------------------------------------------------------#
#-----------------------------------------------------------------------------#
def _scan_U2(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.69, +0.69])
    
    else:
        
        self.U2 = val
       
        set_multipoles(self)

        return 1

def _scan_U1(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-3.33, +3.33])
    
    else:
        
        self.U1 = val
       
        set_multipoles(self)

        return 1

def _scan_U4(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.73, +0.73])
    
    else:
        
        self.U4 = val
       
        set_multipoles(self)

        return 1

def _scan_U5(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.07, +0.07])
    
    else:
        
        self.U5 = val
       
        set_multipoles(self)

        return 1

def _scan_U3(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.13, +0.13])
    
    else:
        
        self.U3 = val
       
        set_multipoles(self)

        return 1

def _scan_Ex(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.05, +0.05])
    
    else:
        
        self.Ex = val
       
        set_multipoles(self)

        return 1

def _scan_Ey(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.73, +0.73])
    
    else:
        
        self.Ey = val
       
        set_multipoles(self)

        return 1

def _scan_Ez(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.65, +0.65])
    
    else:
        
        self.Ez = val
       
        set_multipoles(self)

        return 1

