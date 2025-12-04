import numpy as np
import matplotlib.pyplot as plt
from artiq_controller import FindOptimalE

# =============================================================================
# 1) Configuration Settings
# =============================================================================

# Define the list of RF amplitudes you want to scan
# Modify this list based on your experimental needs (e.g., dBm or Voltage)
RF_AMPLITUDES_TO_SCAN = [0.5, 1.0, 1.5, 2.0, 2.5] 

# General ARTIQ Sequence Settings
general_config = {
    "histogram_on": True,
    "bin_width": 1.0,
    "histogram_refresh": 1000,
    "mesh_voltage": 120,
    "MCP_front": 400,
    "threshold_voltage": 60,
    "wait_time": 90,
    "load_time": 210,
    "frequency_422": 709.078300,
    "frequency_390": 768.708843,
    "RF_on": True,
    "RF_frequency": 1.732,
    "ext_pulse_length": 900,
    "ext_pulse_level": 15.0,
    "U1": 0, "U3": 0, "U4": 0, "U5": 0,
    "U2": -0.18,
    # "RF_amplitude" will be updated dynamically in the loop
}

# Bayesian Optimizer Settings
optimizer_config = {
    "optimize_target": "ratio_signal",
    "max_iteration": 50,
    "min_iteration": 5,
    "init_sample_size": 10,
    "tolerance": 5e-3,
    "converge_count": 3,
    "n_candidate_run": 1024,
    "n_candidate_anal": 4096,
    "min_Ex": -0.25, "max_Ex": 0.05,
    "min_Ey": -0.05, "max_Ey": 0.2,
    "min_Ez": -0.1, "max_Ez": 0.1,
    "no_of_repeats": 3000,
}

# =============================================================================
# 2) Helper Functions
# =============================================================================

def calculate_trimmed_mean(data_array):
    """
    Calculates the mean and std of a dataset after dropping the max and min values.
    
    Args:
        data_array (np.array): A 1D array of floats (e.g., 5 runs of Ex).
        
    Returns:
        tuple: (mean, std) of the trimmed data.
               Returns (nan, nan) if data points are insufficient (< 3).
    """
    n = len(data_array)
    if n < 3:
        print("Warning: Not enough data points to drop max/min. Using raw mean.")
        return np.mean(data_array), np.std(data_array)
    
    # Sort the array to easily isolate min and max
    sorted_data = np.sort(data_array)
    
    # Slice to remove the first (min) and last (max) elements
    # [1:-1] includes everything from index 1 up to (but not including) the last index
    trimmed_data = sorted_data[1:-1]
    
    mean_val = np.mean(trimmed_data)
    std_val = np.std(trimmed_data) # Standard deviation of the remaining points
    
    return mean_val, std_val

# =============================================================================
# 3) Main Batch Process
# =============================================================================

def run_rf_scan_batch(n_repeats=5):
    """
    Main function to iterate through RF amplitudes, run optimizer multiple times,
    process the data (trimmed mean), and plot the results.
    """
    
    # Storage for final results to plot
    # Structure: [RF_val1, RF_val2, ...]
    results_Ex = [] 
    results_Ey = []
    results_Ez = []
    
    # Storage for error bars (standard deviation of trimmed data)
    errors_Ex = []
    errors_Ey = []
    errors_Ez = []

    print(f"Starting Batch Scan for RF Amplitudes: {RF_AMPLITUDES_TO_SCAN}")
    print(f"Repeats per point: {n_repeats} (Max/Min will be dropped)")
    
    # --- Outer Loop: Iterate through different RF Amplitudes ---
    for rf_amp in RF_AMPLITUDES_TO_SCAN:
        
        print(f"\n>>> Processing RF Amplitude = {rf_amp} ...")
        
        # Update the configuration dictionary with current RF value
        general_config["RF_amplitude"] = rf_amp
        
        # Temporary storage for the N runs of this specific RF amp
        current_rf_runs_model = [] # We use the 'Model' E as it's generally more stable
        
        # --- Inner Loop: Repeat Optimization N times ---
        for i in range(n_repeats):
            print(f"    Run {i+1}/{n_repeats}...", end=" ", flush=True)
            
            try:
                # Initialize Controller
                opt = FindOptimalE()
                
                # Combine configs
                run_kwargs = {}
                run_kwargs.update(optimizer_config)
                run_kwargs.update(general_config)
                
                # Execute Optimization
                # We prioritize E_best_model (GP prediction) over E_best_obs (Single shot)
                # as the model output is less susceptible to shot noise.
                _, E_best_model = opt.run(**run_kwargs)
                
                if E_best_model is not None:
                    current_rf_runs_model.append(E_best_model)
                    print(f"Done. Model E: {E_best_model}")
                else:
                    print("Failed (Optimization returned None).")
                    
            except Exception as e:
                print(f"Error in run {i+1}: {e}")

        # --- Data Processing: Drop Max/Min and Average ---
        # Convert list of tuples [(Ex,Ey,Ez), ...] to numpy array for slicing
        # shape: (n_successful_runs, 3)
        data_matrix = np.array(current_rf_runs_model)
        
        if len(data_matrix) > 0:
            # Process Ex (Column 0)
            mu_x, std_x = calculate_trimmed_mean(data_matrix[:, 0])
            results_Ex.append(mu_x)
            errors_Ex.append(std_x)
            
            # Process Ey (Column 1)
            mu_y, std_y = calculate_trimmed_mean(data_matrix[:, 1])
            results_Ey.append(mu_y)
            errors_Ey.append(std_y)
            
            # Process Ez (Column 2)
            mu_z, std_z = calculate_trimmed_mean(data_matrix[:, 2])
            results_Ez.append(mu_z)
            errors_Ez.append(std_z)
            
            print(f"    -> Trimmed Mean Result @ RF={rf_amp}:")
            print(f"       Ex: {mu_x:.4f} +/- {std_x:.4f}")
            print(f"       Ey: {mu_y:.4f} +/- {std_y:.4f}")
            print(f"       Ez: {mu_z:.4f} +/- {std_z:.4f}")
        else:
            print("    -> All runs failed for this RF amplitude.")
            results_Ex.append(np.nan)
            results_Ey.append(np.nan)
            results_Ez.append(np.nan)
            errors_Ex.append(np.nan)
            errors_Ey.append(np.nan)
            errors_Ez.append(np.nan)

    # =========================================================================
    # 4) Plotting
    # =========================================================================
    print("\nPlotting results...")
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 12), sharex=True)
    
    # Plot Ex
    ax1.errorbar(RF_AMPLITUDES_TO_SCAN, results_Ex, yerr=errors_Ex, fmt='-o', capsize=5, color='tab:blue')
    ax1.set_ylabel('Optimal Ex [V/m]')
    ax1.set_title('Optimal E-field vs RF Amplitude (Trimmed Mean of 5 runs)')
    ax1.grid(True, alpha=0.3)
    
    # Plot Ey
    ax2.errorbar(RF_AMPLITUDES_TO_SCAN, results_Ey, yerr=errors_Ey, fmt='-o', capsize=5, color='tab:orange')
    ax2.set_ylabel('Optimal Ey [V/m]')
    ax2.grid(True, alpha=0.3)
    
    # Plot Ez
    ax3.errorbar(RF_AMPLITUDES_TO_SCAN, results_Ez, yerr=errors_Ez, fmt='-o', capsize=5, color='tab:green')
    ax3.set_ylabel('Optimal Ez [V/m]')
    ax3.set_xlabel('RF Amplitude (Config Value)')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Start the batch process
    run_rf_scan_batch(n_repeats=5)
