import numpy as np
import shutil
from configparser import ConfigParser

import scan_functions as sf
from base_sequences import set_multipoles
from helper_functions import latin_hypercube, normalize_coordinates, normalize_values, gaussian_process_hyperparameters, gaussian_process_predictor

# ===================================================================
# 1) Master function for analyze
def ofat_analyze(self):

    reset_scan_parameter(self)
    close_instruments(self)
    save_data_or_exit(self)

def doe_analyze(self):

    reset_scanned_parameters(self)
    close_instruments(self)
    save_data_or_exit(self)
    if self.scan_ok and self.utility_mode == "DOE Scan":
        save_to_doe_table(self)

def optimizer_analyze(self):

    reset_optimizer_parameters(self)
    close_instruments(self)
    save_data_or_exit(self)
    printout_final_result(self)

# ===================================================================
# 2) Subfunctions for analyze
def reset_scan_parameter(self):

    name = self.scanning_parameter

    # Get correct value and tool for reseting
    initial_value = next((e['val'] for e in self.config_dict if e.get('par') == name), None)

    func = sf._get_scan_function(name)

    # Reset scanning parameter
    func(self, initial_value, [initial_value], scan_check=False)

def reset_scanned_parameters(self):

    print("Resetting all scanned parameters to their default values ...")

    default_values = {item["par"]: item["val"] for item in self.config_dict}

    for param_name in self.setpoints.columns:
        initial_value = default_values[param_name]

        func = sf._get_scan_function(param_name)
        if func:
            func(self, initial_value, [initial_value], scan_check=False)
        else:
            print(f"Parameter {param_name} not reset, because there is no scan function for it.")
            
    print("All scannned paramters with scan functions reset to default")

def reset_optimizer_parameters(self):

    print("Resetting Ex, Ey, and Ez to default [0.0, 0.0, 0.0] ...")

    self.Ex, self.Ey, self.Ez = (0.0, 0.0, 0.0)
    set_multipoles(self)

def close_instruments(self):

    # Close instrument connections created by prepare
    # 1) Close Laser Client
    self.laser.close()
    
    # 2) Close Tickler (DSG821)
    self.tickler.off()
    self.tickler.close()

    # 3) Close RF (RS and Keysight)
    self.rf.off()
    
    # 4) Close Extraction Pulser (BK4053)
    # Should not turn off ext_pulser because it could kill the AOM
    #self.ext_pulser.off()
    self.ext_pulser.close()

def printout_final_result(self):

    # Extract best observed point
    idx = np.argmax(self.y_sampled)
    E_best_obs = self.E_sampled[idx]
    y_best_obs = self.y_sampled[idx]

    # Extract best model solved point
    E_best_model, y_best_model = find_model_optimum(self)

    # Printout result
    print("\n==== Optimization results (find_optimal_E) ====")
    print("Best observed (incumbent):")
    print(f"  value = {y_best_obs}")
    print(f"  E = [{E_best_obs[0]}, {E_best_obs[1]}, {E_best_obs[2]}]")
    print("Best predicted by GP (posterior mean on candidate grid):")
    print(f"  mean = {y_best_model}")
    print(f"  E = [{E_best_model[0]}, {E_best_model[1]}, {E_best_model[2]}]")

def find_model_optimum(self):

    # Extract data for final model
    E_normalized = normalize_coordinates(self.E_sampled, self.bounds)
    y_normalized, _ = normalize_values(self.y_sampled)
    length_scale, variance, noise, xi, _ = gaussian_process_hyperparameters(E_normalized, y_normalized)

    # General testing points for final model
    candidates = latin_hypercube(self.n_candidate_anal, self.bounds)
    candidates_normalized = normalize_coordinates(candidates, self.bounds)

    # Predict with final model
    mu, sigma = gaussian_process_predictor(
        E_normalized, y_normalized, candidates_normalized,
        noise=noise, length_scale=length_scale, variance=variance
    )

    # Final predicted optimum by the model
    idx = np.argmax(mu)
    E_best = candidates[idx]
    y_best = mu[idx]

    return E_best, y_best

# ===================================================================
# 3) Functions for saving data
def save_data_or_exit(self):

    # If there are error records, append to config_dict
    if self.err_list:
        err_entry = {"par": "errors", "val": self.err_list}
        self.config_dict.append(err_entry)

    # Save data
    if self.scan_ok:

        print('Saving data...')
        save_all(self)
        print('Experiment ' + self.basefilename + ' finished.')
        print('Experiment finished.')

    else:

        print('Scan terminated.')

def save_to_doe_table(self):

    results = self.setpoints.copy()

    for col_name in self.fields_to_fill:
        try:
            results[col_name] = self.get_dataset(col_name)
        except Exception:
            print(f"Failed to save data column {col_name}: No such dataset!")

    output_file = f"{self.basefilename}_DOE_results_table.csv"
    results.to_csv(output_file, index=False)

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
