import numpy as np
import pandas as pd
import shutil
from configparser import ConfigParser
import traceback
import datetime
import os

import scan_functions as sf
from base_sequences import set_multipoles
from helper_functions import latin_hypercube, normalize_coordinates, normalize_values, gaussian_process_hyperparameters, gaussian_process_predictor

# ===================================================================
# 1) Master function for analyze
def ofat_analyze(self):

    # 1) Reset devices to default state
    reset_instruments(self)
    close_instruments(self)

    # 2) Save data
    define_ofat_saving_configuration(self)
    define_saving_configuration(self)
    save_data_or_exit(self)

def doe_analyze(self):

    # 1) Reset devices to default state
    reset_instruments(self)
    close_instruments(self)

    # 2) Save data
    define_saving_configuration(self)
    save_data_or_exit(self)

def optimizer_analyze(self):

    # 1) Reset devices to default state
    reset_instruments(self)
    close_instruments(self)

    # 2) Save data
    define_saving_configuration(self)
    define_optimizer_saving_configuration(self)
    save_data_or_exit(self)

    printout_final_result(self)

# ===================================================================
# 2) Subfunctions for analyze
def reset_instruments(self, optimizer=False):

    # Reset devices to default state
    try:
        if optimizer:
            reset_optimizer_parameters(self)
        else:
            reset_scan_parameter(self)
    except Exception:
        print("[Error] Failed to reset scan parameter")
        traceback.print_exc()

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

    param_names = getattr(self, "doe_param_names", self.setpoints.columns)
    for param_name in param_names:
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
    try:
        self.laser.close()
    except Exception:
        print("[Error] Failed to close the laser")
        traceback.print_exc()

    # 2) Close Tickler (DSG821)
    try:
        self.tickler.off()
        self.tickler.close()
    except Exception:
        print("[Error] Failed to close the tickler")
        traceback.print_exc()

    # 3) Close RF (RS and Keysight)
    try:
        self.rf.off()
    except Exception:
        print("[Error] Failed to close the RF")
        traceback.print_exc()
        
    # 4) Close Extraction Pulser (BK4053)
    # Should not turn off ext_pulser because it could kill the AOM
    try:
        self.ext_pulser.close()
    except Exception:
        print("[Error] Failed to close the extraction pulse and AOM controller")
        traceback.print_exc()

    # 5) Close Final Signal Generator (DG4162)
    try:
        self.threshold_detector.off(disable_output=False, kill_socket=True)
    except Exception:
        print("[Error] Failed to close the final signal and RST generator")
        traceback.print_exc()

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
# 3) Define data to save
def define_saving_configuration(self):
    signal_level = "substep" if self.mode in ("Lifetime", "Lifetime_fast") else "scan"
    
    # Set the data going to save
    common_data_to_save = [
            #{'var' : 'arr_of_timestamps',  'name' : 'array of timestamps during extraction'},
            {'var': 'last_frequency_422', 'level': 'scan',       'name': 'array of fetched last frequency from laser lock GUI, actual frequency if the GUI is measuring 422 at the time'},
            {'var': 'last_frequency_390', 'level': 'scan',       'name': 'array of fetched last frequency from laser lock GUI, actual frequency if the GUI is measuring 390 at the time'},
            {'var': 'trapped_signal',     'level': signal_level, 'name': 'array of trapped electron counts'},
            {'var': 'loading_signal',     'level': signal_level, 'name': 'array of loading electron counts'},
            {'var': 'lost_signal',        'level': signal_level, 'name': 'array of kicked out electron counts in the first 15us or during the tickle pulse duration when it is smaller than 15us'},
            {'var': 'ratio_signal',       'level': signal_level, 'name': 'array of trapped counts / loading counts'},
            {'var': 'ratio_lost',         'level': signal_level, 'name': 'array of lost counts / loading counts'},
            {'var': 'scan_result',        'level': 'scan',       'name': 'array of recorded counts for counting mode'},
            {'var': 'time_cost',          'level': 'scan',       'name': 'array of time cost for each experiment scan'},
            {'var': 'act_RF_amplitude',   'level': 'scan',       'name': 'array of actual RF amplitude'},
    ]

    # save sequence file name
    self.data_to_save.extend(common_data_to_save)
    self.config_dict.append({'par' : 'sequence_file', 'val' : self.sequence_filename, 'cmt' : 'Filename of the main sequence file'})

    if self.mode in ("Lifetime", "Lifetime_fast"):
        tao = [{'var': 'lifetime', 'level': 'scan', 'name': 'lifetime'}]
        self.data_to_save.extend(tao)

    get_basefilename(self)

def define_ofat_saving_configuration(self):

    self.data_to_save.append({'var': 'arr_of_setpoints', 'level': 'scan', 'name': 'array of setpoints'})

    if self.mode == 'Counting':
        self.data_to_save.append({'var': 'scan_x', 'level': 'scan', 'name': 'array of setpoints for counting mode, duplicate but in order to be compatible with applet'})

def define_optimizer_saving_configuration(self):

    optimizer_data_to_save = [
        {'var': 'e_trace', 'level': 'scan', 'name': 'array of electric field trace'},
        {'var': 'y_best',  'level': 'scan', 'name': 'array of best signal until now'},
        {'var': 'ei',      'level': 'scan', 'name': 'array of expected improvement'}
    ]
    self.data_to_save.extend(optimizer_data_to_save)

# ===================================================================
# 4) Functions for saving data
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

def _dataset_len(self, key):
    return len(np.asarray(self.get_dataset(key)))


def _scan_row_count(self):
    if getattr(self, "utility_mode", None) == "DOE Scan" and hasattr(self, "setpoints"):
        return len(self.setpoints)
    if hasattr(self, "scan_values"):
        return len(self.scan_values)
    return _dataset_len(self, "time_cost")


def _build_scan_result_table(self):
    """
    Build one-row-per-scan-point table for OFAT/DOE/optimizer.
    """
    n_scan = _scan_row_count(self)
    out = pd.DataFrame()

    # DOE: include shuffled execution order table with row identity columns.
    if getattr(self, "utility_mode", None) == "DOE Scan" and hasattr(self, "setpoints"):
        points = self.setpoints.reset_index(drop=True)
        if len(points) == n_scan:
            out = points.copy()
    else:
        out["scan_index"] = np.arange(n_scan, dtype=int)

    for hlp in self.data_to_save:
        if hlp.get("level", "scan") == "substep":
            continue
        key = hlp["var"]
        arr = np.asarray(self.get_dataset(key))
        if len(arr) != n_scan:
            # Optimizer BO traces are indexed by optimizer iteration (0..max_iteration-1),
            # while scan table is indexed by full experiment steps (init + BO).
            if (
                hasattr(self, "init_sample_size")
                and key in {"y_best", "ei", "length_scale", "best_rel_noise", "optimizer_x"}
                and len(arr) == int(getattr(self, "max_iteration", -1))
            ):
                full = np.full(n_scan, np.nan)
                i0 = int(self.init_sample_size)
                full[i0:i0 + len(arr)] = arr
                arr = full
            else:
                continue

        if key == "e_trace":
            arr2 = np.asarray(arr, dtype=float)
            if arr2.ndim == 2 and arr2.shape[1] >= 3:
                out["ex_trace"] = arr2[:, 0]
                out["ey_trace"] = arr2[:, 1]
                out["ez_trace"] = arr2[:, 2]
            continue

        if key == "arr_of_setpoints" and hasattr(self, "scanning_parameter"):
            # OFAT/single-parameter scans: use the physical parameter name as CSV column.
            col = str(self.scanning_parameter)
            if col and (col not in out.columns):
                out[col] = arr
                continue

        if arr.ndim == 1:
            out[key] = arr

    if "doe_run_order" in out.columns:
        cols = ["doe_run_order"] + [c for c in out.columns if c != "doe_run_order"]
        out = out[cols]

    return out


def _build_substep_result_table(self):
    """
    Build one-row-per-substep table (lifetime modes only).
    """
    if self.mode not in ("Lifetime", "Lifetime_fast"):
        return None

    is_doe = getattr(self, "utility_mode", None) == "DOE Scan" and hasattr(self, "setpoints")
    n_scan = _scan_row_count(self)
    trapped = np.asarray(self.get_dataset("trapped_signal"))
    n_sub = len(trapped)
    if n_scan <= 0 or n_sub <= n_scan:
        return None

    n_rep = max(1, int(getattr(self, "lifetime_points_per_scan", n_sub // n_scan)))
    scan_index = np.repeat(np.arange(n_scan, dtype=int), n_rep)[:n_sub]
    substep_index = np.tile(np.arange(n_rep, dtype=int), n_scan)[:n_sub]
    base_cols = {
        "substep_index": substep_index,
        "global_index": np.arange(n_sub, dtype=int),
    }
    if not is_doe:
        base_cols["scan_index"] = scan_index
    out = pd.DataFrame(base_cols)

    wt_used = np.asarray(self.get_dataset("wait_time_used"))
    reps_used = np.asarray(self.get_dataset("repeats_used"))
    file_used = np.asarray(self.get_dataset("wait_times_file_used"), dtype=object)
    if len(wt_used) == n_sub:
        out["wait_time"] = wt_used
    if len(reps_used) == n_sub:
        out["no_of_repeats"] = reps_used
    if self.mode == "Lifetime" and len(file_used) == n_sub:
        out["wait_times_file"] = file_used

    if is_doe:
        points = self.setpoints.reset_index(drop=True)
        if len(points) == n_scan:
            for col in points.columns:
                out[col] = points[col].to_numpy()[scan_index]

    for hlp in self.data_to_save:
        if hlp.get("level", "scan") != "substep":
            continue
        key = hlp["var"]
        arr = np.asarray(self.get_dataset(key))
        if len(arr) == n_sub:
            out[key] = arr

    # Keep OFAT lifetime x-axis in substep output.
    if not is_doe:
        arr = np.asarray(self.get_dataset("arr_of_setpoints"))
        if len(arr) == n_sub:
            out["arr_of_setpoints"] = arr

    # Remove padded compatibility rows (variable wait-time table lengths).
    if "wait_time" in out.columns:
        valid = np.isfinite(out["wait_time"].to_numpy(dtype=float))
        out = out.loc[valid].reset_index(drop=True)

    if "doe_run_order" in out.columns:
        cols = ["doe_run_order"] + [c for c in out.columns if c != "doe_run_order"]
        out = out[cols]

    return out


def save_csv_tables(self):
    scan_df = _build_scan_result_table(self)
    scan_df.to_csv(f"{self.basefilename}_scan_result.csv", index=False)

    sub_df = _build_substep_result_table(self)
    if sub_df is not None:
        sub_df.to_csv(f"{self.basefilename}_substep_result.csv", index=False)

def save_all(self):

    # CSV-first outputs
    save_csv_tables(self)
    if getattr(self, "legacy_dataset_files", False):
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
