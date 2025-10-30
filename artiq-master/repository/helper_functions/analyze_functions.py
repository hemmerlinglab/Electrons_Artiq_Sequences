import os.path
import datetime
import shutil
from configparser import ConfigParser

# ===================================================================
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

# ===================================================================
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

# ===================================================================
# 3) Functions for saving data
def save_all(self):

    # save all data
    save_all_data(self)

    # save all config
    self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
    save_config(self)
    
    # add scan to list
    add_scan_to_list(self)

def save_all_data(self):
    # loops over data_to_save and saves all data sets in the array self.data_to_save
    for hlp in self.data_to_save:
        
        try:
            # transform into numpy arrays
            arr = np.array(self.get_dataset(hlp['var']))
       
            # Write Data to Files
            f_hlp = open(self.basefilename + '_' + hlp['var'],'w')
        
            np.savetxt(f_hlp, arr, delimiter=",")
    
        except:
            
            arr = self.get_dataset(hlp['var'])

            for k in range(len(arr)):
                f_hlp.write(str(arr[k]) + '\n')        

        f_hlp.close()

def add_scan_to_list(self):

    # Write Data to Files
    f_hlp = open(self.datafolder + '/' + self.today + '/' + 'scan_list_' + self.today, 'a')
    f_hlp.write(self.scan_timestamp + '\n')
    f_hlp.close()

def save_config(self):

    # save run configuration
    # creates and overwrites config file
    # self should has a config_dict
    # self.config_dict is an array of dictionaries
    # self.config_dict[0] = {
    #    'par': <parameter name>,
    #    'val': <parameter value>,
    #    'unit': <parameter unit>, (optional)
    #    'cmt': <parameter comment> (optional)
    #    }

    optional_parameters = ['unit', 'cmt']        
    conf_filename = self.basefilename + '_conf'

    # use ConfigParser to save config options
    config = ConfigParser()

    # create config file
    conf_file = open(conf_filename, 'w')
    print('Config file written.')

    # add scan name to config file
    config['Scan'] = {'filename' : self.basefilename}

    # toggle through dictionary and add the config categories
    for d in self.config_dict:
        config[d['par']] = {'val' : d['val']}

        for opt in optional_parameters:
            if opt in d.keys():
                config[d['par']].update({opt : d[opt]})

    config.write(conf_file)

    # save also the sequence file 
    #print(config['sequence_file']['val'])
    #print(self.basefilename + '_sequence')
    shutil.copyfile(config['sequence_file']['val'], self.basefilename + '_sequence')

    conf_file.close()