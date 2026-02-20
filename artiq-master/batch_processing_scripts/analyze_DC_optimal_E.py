import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
from pathlib import Path
from datetime import datetime
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/artiq_controller")
from artiq_controller import FindOptimalE
from helper_functions import load_data

SAVE_DIR = Path("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/result")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

RUN_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DATE = RUN_TAG[:8]  # "YYYYMMDD"

OUT_DIR = SAVE_DIR / RUN_DATE
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# 1) Configuration Settings
# =============================================================================

# Define the list of RF amplitudes or U2 you want to scan
# Modify this list based on your experimental needs (e.g., dBm or Voltage)
PARAMETERS = ["RF_amplitude", "U2"]
SCANNING = 1    # 0 = RF_amplitude, 1 = U2
VALUES_TO_SCAN = np.linspace(+0.10, -0.60, 36)
#[-0.40, -0.35, -0.30, -0.25, -0.21, -0.18, -0.15, -0.13, -0.11, -0.10]

param_scan = PARAMETERS[SCANNING]

# General ARTIQ Sequence Settings
general_config = {
    "histogram_on": True,
    "bin_width": 1.0,
    "histogram_refresh": 4000,
    "mesh_voltage": 120,
    "MCP_front": 400,
    "threshold_voltage": 60,
    "wait_time": 90,
    "load_time": 210,
    "frequency_422": 709.079620,
    "frequency_390": 768.708843,
    "RF_on": True,
    "RF_amp_mode": "setpoint",
    "RF_frequency": 1.732,
    "ext_pulse_length": 900,
    "ext_pulse_level": 15.0,
    "U1": 0, "U3": 0, "U4": 0, "U5": 0,
    "RF_amplitude": 2.50,
    # param_scan will be updated dynamically in the loop
}

# Bayesian Optimizer Settings
optimizer_config = {
    "optimize_target": "ratio_signal",
    "max_iteration": 100,
    "min_iteration": 10,
    "init_sample_size": 20,
    "tolerance": 5e-3,
    "converge_count": 3,
    "n_candidate_run": 1024,
    "n_candidate_anal": 4096,
    "min_Ex": -0.35, "max_Ex": 0.15,
    "min_Ey": -0.25, "max_Ey": 0.25,
    "min_Ez": -0.10, "max_Ez": 0.40,
    "no_of_repeats": 4000,
}

# =============================================================================
# 2) Helper Functions
# =============================================================================

def calculate_trimmed_mean(data_array, trim_percentage: float = 0.1, trim_minimum: int = 1):
    """
    Calculates the mean and std of a dataset after dropping the max and min values.

    Args:
        data_array (np.array): A 1D array of floats (e.g., 5 runs of Ex).

    Returns:
        tuple: (mean, std) of the trimmed data.
               Returns (nan, nan) if data points are insufficient (< 3).
    """

    n = len(data_array)

    # Make sure trim is an integer so we can use it in slicing
    trim = int(max(n * trim_percentage, trim_minimum))
    trim_safe = min(trim, (n - 1) // 2)

    if trim == 0:
        print("Warning: Not enough data points to drop max/min. Using raw mean.")
        return np.mean(data_array), np.std(data_array)

    if trim_safe < trim:
        print(f"Warning: Not enough data points to drop {trim} points, "
              f"dropping {trim_safe} points instead.")
        # Use the safe value for actual trimming
        trim = trim_safe

    # Sort the array to easily isolate min and max
    sorted_data = np.sort(data_array)

    # Slice to remove the first (min) and last (max) elements
    trimmed_data = sorted_data[trim:-trim] if trim > 0 else sorted_data

    mean_val = np.mean(trimmed_data)
    std_val = np.std(trimmed_data)  # Standard deviation of the remaining points

    return mean_val, std_val


def analyze_data(data_matrix, param_name, scan_value):
    """
    Compute trimmed means/stds for Ex, Ey, Ez for a given RF amplitude.
    Returns:
        means: (mu_x, mu_y, mu_z)
        stds:  (std_x, std_y, std_z)
    """

    mu_x, std_x = calculate_trimmed_mean(data_matrix[:, 0])
    mu_y, std_y = calculate_trimmed_mean(data_matrix[:, 1])
    mu_z, std_z = calculate_trimmed_mean(data_matrix[:, 2])

    print(f"    -> Trimmed Mean Result @ {param_name}={scan_value}:")
    print(f"       Ex: {mu_x:.4f} +/- {std_x:.4f}")
    print(f"       Ey: {mu_y:.4f} +/- {std_y:.4f}")
    print(f"       Ez: {mu_z:.4f} +/- {std_z:.4f}")

    return (mu_x, mu_y, mu_z), (std_x, std_y, std_z)


def get_actual_RF_amplitude(timestamp):

    # Calculate data filepath
    data_directory = "/home/electrons/software/data"
    date, _ = timestamp.split("_")
    path = f"{data_directory}/{date}/{timestamp}_act_RF_amplitude"

    # Analyze data
    data = np.genfromtxt(path, delimiter=",")
    data_nonzero = data[data != 0]
    mean, std = calculate_trimmed_mean(data_nonzero)

    return mean, std

# =============================================================================
# 3) Main Batch Process
# =============================================================================

def run_scan_batch(n_repeats=5):
    """
    Main function to iterate through RF amplitudes, run optimizer multiple times,
    process the data (trimmed mean), and collect the results.

    Returns
    -------
    results, errors, rf_actual_means, rf_actual_stds

    - results[kind][component] -> list of means per RF point
    - errors[kind][component]  -> list of stds per RF point
    - rf_actual_means          -> list of trimmed-mean actual RF amplitudes per setpoint
    - rf_actual_stds           -> list of stds of actual RF amplitudes per setpoint
    """

    COMPONENTS = ("Ex", "Ey", "Ez")
    SIGNALS = ["loading_signal", "trapped_signal", "lost_signal", "ratio_signal", "ratio_lost"]
    results = {
        "Observed": {comp: [] for comp in COMPONENTS},
        "Model":    {comp: [] for comp in COMPONENTS},
    }
    errors = {
        "Observed": {comp: [] for comp in COMPONENTS},
        "Model":    {comp: [] for comp in COMPONENTS},
    }

    # For x-axis: actual RF amplitudes per setpoint
    rf_actual_means = []
    rf_actual_stds = []

    # For y-axis: trap performances
    y_means = {s: [] for s in SIGNALS}
    y_stds  = {s: [] for s in SIGNALS}

    print(f"Starting Batch Scan for {param_scan}: {VALUES_TO_SCAN}")
    print(f"Repeats per point: {n_repeats} (Max/Min will be dropped)")

    # --- Outer Loop: Iterate through different RF Amplitudes (setpoints) ---
    for scan_value in VALUES_TO_SCAN:

        print(f"\n>>> Processing value = {scan_value} (setpoint) ...")

        # Update the configuration dictionary with current RF value
        general_config[param_scan] = scan_value

        # Temporary storage for the N runs of this specific RF amp
        # each is a list of (Ex, Ey, Ez)
        current_rf_runs = {
            "Observed": [],
            "Model": [],
        }

        # Temporary storage for actual RF amplitude of each run (measured)
        current_rf_actuals = []

        # Temporary storage for y data of each run
        current_y = {s: [] for s in SIGNALS}

        # --- Inner Loop: Repeat Optimization N times ---
        for i in range(n_repeats):
            print(f"Run {i+1}/{n_repeats}...")

            try:
                # Initialize Controller
                opt = FindOptimalE()

                # Combine configs
                run_kwargs = {}
                run_kwargs.update(optimizer_config)
                run_kwargs.update(general_config)

                # Execute Optimization
                E_best_observed, E_best_model, timestamp = opt.run(**run_kwargs)

                E_best = {
                    "Observed": E_best_observed,
                    "Model":    E_best_model,
                }

                for kind in ("Observed", "Model"):
                    val = E_best[kind]
                    if val is not None:
                        current_rf_runs[kind].append(val)
                        print(f"    Done. {kind} E: ({val[0]:.3f}, {val[1]:.3f}, {val[2]:.3f})")
                    else:
                        print(f"    Failed ({kind} optimization returned None).")

                # Get actual RF amplitude for this run (from data file)
                try:
                    rf_mean_run, rf_std_run = get_actual_RF_amplitude(timestamp)
                    current_rf_actuals.append(rf_mean_run)
                    print(f"    Actual RF amplitude (run mean): {rf_mean_run:.4f}")
                except Exception as e_rf:
                    print(f"    Warning: could not get actual RF amplitude "
                          f"for timestamp {timestamp}: {e_rf}")

                # Get signals for this run (from data file)
                _, ys = load_data(timestamp, ynames=SIGNALS)
                for s in SIGNALS:
                    arr = ys.get(s, None)
                    current_y[s].append(np.nanmax(arr) if arr is not None else np.nan)

            except Exception as e:
                print(f"Error in run {i+1}: {e}")

        # --- Aggregate actual RF amplitude for this setpoint ---
        if current_rf_actuals:
            rf_mean, rf_std = calculate_trimmed_mean(np.array(current_rf_actuals))
        else:
            rf_mean, rf_std = (np.nan, np.nan)

        rf_actual_means.append(rf_mean)
        rf_actual_stds.append(rf_std)

        # --- Calculate the correct y values ---
        for s in SIGNALS:
            mu, sd = calculate_trimmed_mean(np.array(current_y[s], dtype=float))
            y_means[s].append(mu)
            y_stds[s].append(sd)

        # --- Data Processing: Drop Max/Min and Average E-field components ---
        for kind in ("Observed", "Model"):
            runs = current_rf_runs[kind]
            # Convert list of tuples [(Ex,Ey,Ez), ...] to numpy array
            data_matrix = np.array(runs) if runs else np.empty((0, 3))

            means, stds = analyze_data(data_matrix, param_scan, scan_value)
            # means = (mu_x, mu_y, mu_z)
            # stds  = (std_x, std_y, std_z)

            for idx, comp in enumerate(COMPONENTS):
                results[kind][comp].append(means[idx])
                errors[kind][comp].append(stds[idx])

    return results, errors, rf_actual_means, rf_actual_stds, y_means, y_stds


# =========================================================================
# 4) Plotting
# =========================================================================
def do_plot(
    x_values,
    series_results,  # e.g. results["Observed"]
    series_errors,   # e.g. errors["Observed"]
    title_suffix="",
    param_name=param_scan,
    x_label="Actual RF Amplitude",
):
    """
    Create a figure with 3 subplots (Ex, Ey, Ez) for a single series
    (e.g. Observed OR Model).

    x_values:       x-axis values (e.g. actual RF amplitudes)
    series_results: dict with keys "Ex", "Ey", "Ez"
    series_errors:  dict with keys "Ex", "Ey", "Ez"

    Returns
    -------
    fig, axes   # axes is (ax1, ax2, ax3)
    """

    components = ["Ex", "Ey", "Ez"]
    ylabels = [
        "Optimal Ex [V/m]",
        "Optimal Ey [V/m]",
        "Optimal Ez [V/m]",
    ]
    colors = ["tab:blue", "tab:orange", "tab:green"]

    if title_suffix:
        full_title = f"Optimal E-field vs {param_name} - {title_suffix}"
    else:
        full_title = f"Optimal E-field vs {param_name}"

    fig, axes = plt.subplots(3, 1, figsize=(8, 12), sharex=True)

    for ax, comp, ylabel, color in zip(axes, components, ylabels, colors):
        ax.errorbar(
            x_values,
            series_results[comp],
            yerr=series_errors[comp],
            fmt='-o',
            capsize=5,
            color=color,
        )
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[0].set_title(full_title)
    axes[-1].set_xlabel(x_label)

    plt.tight_layout()
    return fig, axes


def plot_signals_2x3(
    x_values,
    y_means,   # dict: signal -> list
    y_stds,    # dict: signal -> list
    signals,
    x_label,
    out_png="scan_signals_2x3.png",
    title="Trap performance signals vs scan parameter",
):
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
    axes = axes.ravel()

    for i, s in enumerate(signals):
        ax = axes[i]
        ax.errorbar(
            x_values,
            y_means[s],
            yerr=y_stds[s],
            fmt="-o",
            capsize=4,
        )
        ax.set_title(s)
        ax.grid(True, alpha=0.3)

    # 6th subplot (empty)
    ax_empty = axes[len(signals)]
    ax_empty.axis("off")

    # x label only on bottom row (optional)
    for ax in axes[3:5]:  # bottom row, first two used (since last is off)
        ax.set_xlabel(x_label)

    fig.suptitle(title, fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_png, dpi=300)
    plt.close(fig)
    print(f"[Save] signals grid -> {out_png}")


# =========================================================================
# 5) Main
# =========================================================================

if __name__ == "__main__":

    results, errors, rf_actual_means, rf_actual_stds, y_means, y_stds = run_scan_batch(n_repeats=9)

    if param_scan == "RF_amplitude":
        x_vals = rf_actual_means
        xlabel = "Actual RF Amplitude"
    else:
        x_vals = VALUES_TO_SCAN
        xlabel = param_scan

    fig_obs, _ = do_plot(x_vals, results["Observed"], errors["Observed"], title_suffix="Observed", x_label=xlabel)
    fig_mod, _ = do_plot(x_vals, results["Model"],    errors["Model"],    title_suffix="Model",    x_label=xlabel)

    fig_obs.savefig(OUT_DIR / "scan_observed.png", dpi=300)
    fig_mod.savefig(OUT_DIR / "scan_model.png", dpi=300)

    SIGNALS = ["loading_signal", "trapped_signal", "lost_signal", "ratio_signal", "ratio_lost"]
    plot_signals_2x3(
        x_vals, y_means, y_stds, SIGNALS,
        x_label=xlabel,
        out_png=str(OUT_DIR / "scan_signals_2x3.png"),
        title=f"Signals vs {param_scan}",
    )
