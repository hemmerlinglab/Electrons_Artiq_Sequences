import numpy as np
import matplotlib
matplotlib.use("Agg")   # Use non-interactive backend (no Qt / xcb)
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import json
import csv
import argparse

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/artiq_controller")
from artiq_controller import SingleParameterScan

# =============================================================================
# 1) Configuration
# =============================================================================

try:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offset", type=float, required=True, help="Top electrode offset (+OFFSET), bottom uses (-OFFSET)")
    args = parser.parse_args()

    OFFSET = float(args.offset)

except Exception:
    OFFSET = 0.0

SAVE_DIR = Path("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/result")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Layout of electrodes in the final 4x5 subplot figure
ROWS = [
    ["tl1", "tl2", "tl3", "tl4", "tl5"],
    ["tr1", "tr2", "tr3", "tr4", "tr5"],
    ["bl1", "bl2", "bl3", "bl4", "bl5"],
    ["br1", "br2", "br3", "br4", "br5"],
]
ALL_ELECTRODES = [e for row in ROWS for e in row]


def offset_param_name(electrode: str) -> str:
    """
    Convert an electrode label (e.g. 'tl1') into the ARTIQ parameter name
    used in single_parameter_scan, e.g. 'offset_tl1'.
    """
    return f"offset_{electrode}"


# Scan range for single_parameter_scan
SCAN_CONFIG = {
    "min_scan": -20.0,    # offset lower bound
    "max_scan": 20.0,     # offset upper bound
    "steps":  41,       # number of points
}

# General ARTIQ parameters for the sequence (passed through **extra_params)
GENERAL_SEQ_CONFIG = {
    "mode": "Trapping",
    "histogram_on": True,
    "bin_width": 1.0,
    "histogram_refresh": 10000,
    "mesh_voltage": 120,
    "MCP_front": 400,
    "threshold_voltage": 60,
    "wait_time": 90,
    "load_time": 210,
    "no_of_repeats": 10000,
    "frequency_422": 709.076660,
    "frequency_390": 768.708843,
    "RF_on": True,
    "RF_frequency": 1.732,
    "ext_pulse_length": 900,
    "ext_pulse_level": 15.0,
    "U1": 0.0, "U3": 0.0, "U4": 0.0, "U5": 0.0,
    "Ex": -0.20, "Ey": 0.05, "Ez": 0.03,
    "U2": -0.225,
    "RF_amplitude": 2.5,
    "tickle_on": False,
}

# Generate offsets
OFFSET_CONFIG = {}
for row in ROWS:
    for e in row:
        is_top = e.startswith(("tl", "tr"))
        OFFSET_CONFIG[f"offset_{e}"] = float(OFFSET if is_top else -OFFSET)

# Data directory and filename template for the single_parameter_scan output
DATA_DIRECTORY = "/home/electrons/software/data"

# Example filename pattern:
#   /home/electrons/software/data/20241205/20241205_153000_arr_of_setpoints (no .csv)
FILE_TEMPLATE = "{timestamp}_{param}"

# Signals to plot
Y_SIGNALS = [
    "trapped_signal",
    "lost_signal",
    "ratio_signal",
    "ratio_lost",
]

X_SIGNAL = "arr_of_setpoints"

MULTI_FILE_TEMPLATE = "{timestamp}_{dataset}"

# =============================================================================
# 2) Data loading for a single scan
# =============================================================================

def load_single_scan_data(timestamp: str, y_dataset: str):
    """
    Load one single_parameter_scan result from disk, using the new
    multi-file layout.

    Parameters
    ----------
    timestamp : str
        Timestamp string embedded in the ARTIQ output
        (e.g. '20251202_104918'). Used to reconstruct the data path:
        /data/YYYYMMDD/timestamp_dataset.csv

    y_dataset : str
        Name of the Y dataset to load, e.g.:
            'trapped_signal', 'lost_signal',
            'ratio_signal', 'ratio_lost'.

    Returns
    -------
    x_values : np.ndarray
        The scanned parameter values (from arr_of_setpoints).
    y_values : np.ndarray
        The corresponding measured values for the chosen dataset.
    """
    date, _ = timestamp.split("_", 1)
    base_dir = f"{DATA_DIRECTORY}/{date}"

    # X: setpoints
    x_filename = MULTI_FILE_TEMPLATE.format(timestamp=timestamp,
                                            dataset=X_SIGNAL)
    x_path = f"{base_dir}/{x_filename}"

    # Y: selected dataset
    y_filename = MULTI_FILE_TEMPLATE.format(timestamp=timestamp,
                                            dataset=y_dataset)
    y_path = f"{base_dir}/{y_filename}"

    print(f"  Loading X from: {x_path}")
    print(f"  Loading Y ({y_dataset}) from: {y_path}")

    x_data = np.genfromtxt(x_path, delimiter=",", comments="#")
    y_data = np.genfromtxt(y_path, delimiter=",", comments="#")

    # If files accidentally have more than one column, take the first one.
    if x_data.ndim > 1:
        x_data = x_data[:, 0]
    if y_data.ndim > 1:
        y_data = y_data[:, 0]

    if x_data.shape[0] != y_data.shape[0]:
        raise ValueError(
            f"Length mismatch between X ({x_data.shape[0]}) and "
            f"Y ({y_data.shape[0]}) for timestamp {timestamp}, dataset {y_dataset}"
        )

    return x_data, y_data

# =============================================================================
# 3) Run single_parameter_scan for one electrode
# =============================================================================

def run_scan_for_electrode(electrode: str) -> str:
    """
    Perform a single_parameter_scan for one electrode (e.g. 'tl1')
    and return the resulting timestamp.

    Parameters
    ----------
    electrode : str
        Electrode label such as 'tl1', 'tr3', 'bl2', etc.

    Returns
    -------
    timestamp : str
        Timestamp string returned by SingleParameterScan.run().
    """
    param = offset_param_name(electrode)
    print(f"\n=== Scanning electrode {electrode} (parameter: {param}) ===")

    sps = (
        SingleParameterScan()
        .load_params(GENERAL_SEQ_CONFIG)
        .load_params(OFFSET_CONFIG)
    )

    timestamp = sps.run(
        scanning_parameter=param,
        min_scan=SCAN_CONFIG["min_scan"],
        max_scan=SCAN_CONFIG["max_scan"],
        steps=SCAN_CONFIG["steps"],
    )

    print(f"  single_parameter_scan timestamp = {timestamp}")
    return timestamp

def run_all_scans_get_timestamps():
    """
    Run single_parameter_scan for all electrodes in ALL_ELECTRODES.

    Returns
    -------
    timestamps : dict
        Mapping: electrode -> timestamp string
    """
    timestamps = {}
    for elec in ALL_ELECTRODES:
        ts = run_scan_for_electrode(elec)
        timestamps[elec] = ts
    return timestamps

def load_results_for_dataset(timestamps: dict, y_dataset: str):
    """
    For a given Y dataset name and a dict of per-electrode timestamps,
    load X and Y data for all electrodes.

    Parameters
    ----------
    timestamps : dict
        Mapping: electrode -> timestamp string.
    y_dataset : str
        Name of the Y dataset to load.

    Returns
    -------
    results : dict
        Mapping: electrode -> (x_values, y_values)
    """
    results = {}
    for elec, ts in timestamps.items():
        try:
            x, y = load_single_scan_data(ts, y_dataset)
        except Exception as e:
            print(f"  !!! Failed to load data for {elec}, y={y_dataset}: {e}")
            x = np.array([])
            y = np.array([])
        results[elec] = (x, y)
    return results

# =============================================================================
# 4) Saving: Saving helper functions
# =============================================================================

def fmt_offset_for_filename(x: float, ndp: int = 3) -> str:
    # +0.050 -> p0p050, -0.200 -> m0p200 (safe in bash/globs)
    s = f"{x:+.{ndp}f}"
    return s.replace("+", "p").replace("-", "m").replace(".", "p")

RUN_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_NAME = f"offsetScan_OFF{fmt_offset_for_filename(OFFSET)}_{RUN_TAG}"

def save_timestamps(timestamps: dict):
    # JSON (full metadata)
    json_path = SAVE_DIR / f"{BASE_NAME}_timestamps.json"
    payload = {
        "run_tag": RUN_TAG,
        "OFFSET": float(OFFSET),
        "SCAN_CONFIG": SCAN_CONFIG,
        "GENERAL_SEQ_CONFIG": GENERAL_SEQ_CONFIG,
        "timestamps": timestamps,
    }
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(f"[Save] timestamps JSON -> {json_path}")

    # CSV (quick view)
    csv_path = SAVE_DIR / f"{BASE_NAME}_timestamps.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["electrode", "timestamp"])
        for elec in ALL_ELECTRODES:
            w.writerow([elec, timestamps.get(elec, "")])
    print(f"[Save] timestamps CSV  -> {csv_path}")

# =============================================================================
# 5) Plotting: 4x5 subplots in one figure
# =============================================================================

def plot_results_4x5(results, fig_name="offset_scan_4x5.png"):
    """
    Plot all scans in a 4x5 grid (4 rows, 5 columns) using the ROWS layout.

    Parameters
    ----------
    results : dict
        Mapping electrode -> (x_values, y_values) from run_all_scans().
    fig_name : str
        Output filename for the saved figure.
    """
    fig, axes = plt.subplots(4, 5, figsize=(16, 12), sharex=True, sharey=True)

    for r, row in enumerate(ROWS):
        for c, elec in enumerate(row):
            ax = axes[r, c]
            x, y = results.get(elec, (np.array([]), np.array([])))

            if x.size > 0 and y.size > 0:
                ax.plot(x, y, "-o", markersize=3)
            else:
                # If there is no data, show a small message in the subplot
                ax.text(
                    0.5, 0.5, "no data",
                    transform=ax.transAxes,
                    ha="center", va="center", fontsize=8
                )

            ax.set_title(elec)

            # Only leftmost column shows y label
            if c == 0:
                ax.set_ylabel("Signal")

            # Only bottom row shows x label
            if r == len(ROWS) - 1:
                ax.set_xlabel("offset [V]")

            ax.grid(True, alpha=0.3)

    fig.suptitle("Single-Parameter Scan of Offset Electrodes", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    print(f"\nSaving figure to: {fig_name}")
    fig.savefig(fig_name, dpi=300)
    plt.close(fig)


# =============================================================================
# 5) Main
# =============================================================================
if __name__ == "__main__":
    timestamps = run_all_scans_get_timestamps()

    # save timestamps right away
    save_timestamps(timestamps)

    for y_dataset in Y_SIGNALS:
        print(f"\n\n######## Plotting for Y dataset: {y_dataset} ########\n")
        results = load_results_for_dataset(timestamps, y_dataset=y_dataset)

        fig_path = SAVE_DIR / f"{BASE_NAME}_{y_dataset}.png"
        plot_results_4x5(results, fig_name=str(fig_path))

'''

TIMESTAMPS_20251205 = {
    "tl1": "20251205_140039",
    "tl2": "20251205_140750",
    "tl3": "20251205_141459",
    "tl4": "20251205_142207",
    "tl5": "20251205_142916",
    "tr1": "20251205_143625",
    "tr2": "20251205_144334",
    "tr3": "20251205_145042",
    "tr4": "20251205_145750",
    "tr5": "20251205_150459",
    "bl1": "20251205_151209",
    "bl2": "20251205_151920",
    "bl3": "20251205_152627",
    "bl4": "20251205_153334",
    "bl5": "20251205_154042",
    "br1": "20251205_154753",
    "br2": "20251205_155501",
    "br3": "20251205_160208",
    "br4": "20251205_160915",
    "br5": "20251205_161623",
}

if __name__ == "__main__":
    # Use the timestamps from the already-finished scans
    timestamps = TIMESTAMPS_20251205

    # For each Y dataset, load data from disk and make one 4x5 figure
    for y_dataset in Y_SIGNALS:
        print(f"\n\n######## Plotting for Y dataset: {y_dataset} ########\n")
        results = load_results_for_dataset(timestamps, y_dataset=y_dataset)
        fig_name = f"offset_scan_4x5_{y_dataset}.png"
        plot_results_4x5(results, fig_name=fig_name)
'''