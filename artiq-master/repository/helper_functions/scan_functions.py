import time
import numpy as np

from base_sequences   import set_mesh_voltage, set_multipoles, set_loading_pulse, set_extraction_pulse, set_MCP_voltages, update_detection_time


########################################################################

def scan_parameter(self, my_ind, scan_check = False, reset_value = False):

    # This function allows for scanning any parameter
    # In prepare, it checks whether the scanning function _scan_<parameter> exists and whether the parameter is in range

    if not reset_value:
        val = self.scan_values[my_ind]
    else:
        # reset the value to the one in the parameter listing
        print('Reseting Scanning parameter ...')
        val = eval('self.' + self.scanning_parameter)

    if not scan_check and not reset_value:
        print("Scanning parameter {3}: {2} ({0}/{1})".format(my_ind, len(self.scan_values), val, self.scanning_parameter))
    
    #if self.scanning_parameter == 'mesh_voltage':
    #    return _scan_mesh_voltage(self, val, self.scan_values, scan_check = scan_check)
    #elif self.scanning_parameter == 'RF_frequency':
    #    return _scan_RF_frequency(self, val, self.scan_values, scan_check = scan_check)
    #elif self.scanning_parameter == 'load_time':
    #    return _scan_load_time(self, val, self.scan_values, scan_check = scan_check)
    #elif self.scanning_parameter == 'U2':
    #    return _scan_U2(self, val, self.scan_values, scan_check = scan_check)

    if self.scanning_parameter in ['mesh_voltage', 'MCP_front', '422_frequency', '390_frequency', 'RF_frequency', 'RF_amplitude', 'tickle_frequency', 'tickle_level', 'tickle_pulse_length', 'load_time', 'wait_time', 'ext_pulse_length', 'ext_pulse_amplitude', 'U1', 'U2', 'U3', 'U4', 'U5', 'Ex', 'Ey', 'Ez']:

        return eval('_scan_' + self.scanning_parameter + '(self, val, self.scan_values, scan_check = scan_check)')


    else:
        
        print('Parameter to scan {0} has no scanning function yet'.format(self.scanning_parameter))
        return 0

    return 


########################################################################

def _scan_load_time(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 10000])
    
    else:
        
        self.load_time = val
        update_detection_time(self)

        set_loading_pulse(self)
        set_extraction_pulse(self)

        return 1

    return


########################################################################

def _scan_wait_time(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 10000])
    
    else:
        
        self.wait_time = val
        update_detection_time(self)

        set_extraction_pulse(self)

        return 1

    return


########################################################################

def _scan_ext_pulse_length(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [40, 100000])
    
    else:
        
        self.ext_pulse_length = val
        update_detection_time(self)

        set_extraction_pulse(self)

        return 1

    return


########################################################################

def _scan_ext_pulse_amplitude(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0.01, 20])
    
    else:
        
        self.ext_pulse_amplitude = val

        set_extraction_pulse(self)

        return 1

    return


########################################################################

def _scan_RF_frequency(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [1.5, 1.7])
    
    else:
        
        self.RF_driver.set_freq(val * 1e9)

        return 1

    return


########################################################################

def _scan_RF_amplitude(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-30, 8])
    
    else:
        
        self.RF_driver.set_ampl(val)

        return 1

    return


########################################################################

def _scan_tickle_frequency(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 1000])
    
    else:
        
        self.tickler.set_freq(val)

        return 1

    return


########################################################################

def _scan_tickle_level(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-30, 20])
    
    else:
        
        self.tickler.set_level(val)

        return 1

    return


########################################################################

def _scan_tickle_pulse_length(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [1, 10000])
    
    else:
        
        self.tickle_pulse_length = val

        return 1

    return



########################################################################

def _scan_mesh_voltage(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0.0, 600.0])
    
    else:
        
        set_mesh_voltage(self, val)
        #time.sleep(3)

        return 1

    return


########################################################################

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

    return


########################################################################

def _scan_U2(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.69, +0.69])
    
    else:
        
        self.U2 = val
       
        set_multipoles(self)

        return 1

    return


########################################################################

def _scan_U1(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-3.33, +3.33])
    
    else:
        
        self.U1 = val
       
        set_multipoles(self)

        return 1

    return


########################################################################

def _scan_U4(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.73, +0.73])
    
    else:
        
        self.U4 = val
       
        set_multipoles(self)

        return 1

    return


########################################################################

def _scan_U5(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.07, +0.07])
    
    else:
        
        self.U5 = val
       
        set_multipoles(self)

        return 1

    return


########################################################################

def _scan_U3(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.13, +0.13])
    
    else:
        
        self.U3 = val
       
        set_multipoles(self)

        return 1

    return


########################################################################

def _scan_Ex(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.05, +0.05])
    
    else:
        
        self.Ex = val
       
        set_multipoles(self)

        return 1

    return


########################################################################

def _scan_Ey(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.73, +0.73])
    
    else:
        
        self.Ey = val
       
        set_multipoles(self)

        return 1

    return


########################################################################

def _scan_Ez(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [-0.65, +0.65])
    
    else:
        
        self.Ez = val
       
        set_multipoles(self)

        return 1

    return

########################################################################

def _scan_422_frequency():

    return

########################################################################

def _scan_390_frequency():

    return

########################################################################

def limit_check(par, scan_values, limits):
    
    check = (np.min(scan_values) >= limits[0]) and (np.max(scan_values) <= limits[1])

    if not check:
        print('Scan range out of bounds for parameter {0}.'.format(par))

    return check


