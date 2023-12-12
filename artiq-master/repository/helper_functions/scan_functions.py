import time
import numpy as np

from base_sequences import set_mesh_voltage


########################################################################

def scan_parameter(self, my_ind, scan_check = False, reset_value = False):

    # This function allows for scanning any parameter
    # In prepare, it checks whether the scanning function _scan_<parameter> exists and whether the parameter is in range

    if not reset_value:
        val = self.scan_values[my_ind]
    else:
        # reset the value to the one in the parameter listing
        val = eval('self.' + self.scanning_parameter)

    if not scan_check and not reset_value:
        print("Scanning parameter {3}: {2} ({0}/{1})".format(my_ind, len(self.scan_values), val, self.scanning_parameter))
    
    if self.scanning_parameter == 'mesh_voltage':
        return _scan_mesh_voltage(self, val, self.scan_values, scan_check = scan_check)
    elif self.scanning_parameter == 'RF_frequency':
        return _scan_RF_frequency(self, val, self.scan_values, scan_check = scan_check)
    elif self.scanning_parameter == 'load_time':
        return _scan_load_time(self, val, self.scan_values, scan_check = scan_check)

    else:
        
        print('Parameter to scan {0} has no scanning function yet'.format(self.scanning_parameter))
        return 0

    return 


########################################################################

def _scan_load_time(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 500])
    
    else:
        
        self.load_time = val

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

def _scan_mesh_voltage(self, val, scan_values, scan_check = False):

    if scan_check:

        return limit_check(self.scanning_parameter, scan_values, [0, 500.0])
    
    else:
        
        set_mesh_voltage(self, val)
        #time.sleep(3)

        return 1

    return


########################################################################

def limit_check(par, scan_values, limits):
    
    check = (np.min(scan_values) >= limits[0]) and (np.max(scan_values) <= limits[1])

    if not check:
        print('Scan range out of bounds for parameter {0}.'.format(par))

    return check


