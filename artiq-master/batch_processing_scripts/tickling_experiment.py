import numpy as np
import pandas as pd
import json
from pathlib import Path
import time
from datetime import datetime
import os

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/artiq_controller")
from artiq_controller import SingleParameterScan
from helper_functions import analyze_fine_scan, plot_fine_scan
from experiment_functions import run_with_422_relock

# 0) Save Settings
# ===================================================================
SAVE_DIR = Path("result")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

RUN_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")
SUMMARY_JSON = SAVE_DIR / f"run_summary_{RUN_TAG}.json"
SUMMARY_CSV = SAVE_DIR / f"run_best_models_{RUN_TAG}.csv"

def get_figure_dir(ts):
    date = ts.split("_")[0]
    fig_dir = SAVE_DIR / date
    fig_dir.mkdir(parents=True, exist_ok=True)
    return fig_dir

def get_fine_scan_prefix(ts, U2, RF_amplitude, line_id, rep):
    fig_dir = get_figure_dir(ts)
    prefix = fig_dir / f"fine_U2{U2:+.3f}_RF{RF_amplitude:.2f}_line{line_id:02d}_rep{rep:02d}_{ts}"
    return prefix

def to_builtin(obj):
    import numpy as np
    if isinstance(obj, dict):
        return {str(k): to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_builtin(v) for v in obj]
    if isinstance(obj, tuple):
        return [to_builtin(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj

def best_fit_to_row(best_fit, max_n_peaks=4):
    """
    Flatten best_fit into csv columns.
    best_fit format: {"n_peaks", "r2", "aicc", "popt", ...}
    popt: [c0, amp1, mu1, sigma1, amp2, mu2, sigma2, ...]
    """
    row = {}
    if (best_fit is None) or (best_fit.get("popt", None) is None):
        row["n_peaks"] = 0
        row["r2"] = None
        row["aicc"] = None
        row["c0"] = None
        for i in range(1, max_n_peaks + 1):
            row[f"amp{i}"] = None
            row[f"mu{i}"] = None
            row[f"sigma{i}"] = None
        return row

    popt = best_fit["popt"]
    n = int(best_fit["n_peaks"])
    row["n_peaks"] = n
    row["r2"] = float(best_fit["r2"])
    row["aicc"] = float(best_fit["aicc"])
    row["c0"] = float(popt[0])

    for i in range(1, max_n_peaks + 1):
        if i <= n:
            row[f"amp{i}"] = float(popt[1 + 3*(i-1)])
            row[f"mu{i}"] = float(popt[1 + 3*(i-1) + 1])
            row[f"sigma{i}"] = float(popt[1 + 3*(i-1) + 2])
        else:
            row[f"amp{i}"] = None
            row[f"mu{i}"] = None
            row[f"sigma{i}"] = None
    return row

# 1) Global Settings
# ===================================================================
config = {
    "mode": "Trapping",
    "histogram_on": True,
    "bin_width": 1.0,
    #"histogram_refresh": 16000,
    "mesh_voltage": 120,                    # unit: V
    "MCP_front": 400,                       # unit: V
    "threshold_voltage": 60,                # unit: mV
    "wait_time": 140,                        # unit: us
    "load_time": 260,                       # unit: us
    #"frequency_422": 709.076730,            # unit: THz
    "frequency_390": 768.708843,            # unit: THz
    "laser_failure": "raise error",
    "RF_on": True,
    "RF_amp_mode": "setpoint",
    "RF_frequency": 1.732,                  # unit: GHz
    "ext_pulse_length": 900,                # unit: ns
    "ext_pulse_level": 15.0,                # unit: V (Vpp)
    "U1": 0, "U3": 0, "U4": 0, "U5": 0,     # unit: V/m^2
    "tickle_on": True,
    "tickle_level": -10.0,                  # unit: MHz
    "tickle_pulse_length": 130,              # unit: us
    #"no_of_repeats": 16000
}

LAG = 250                                   # unit: us
NO_OF_REPEATS_ROUGH = 5000                  # 5000 for scan, 3000 for debug
NO_OF_REPEATS_FINE = 20000                  # 20000 for scan, 5000 for debug
STEPSIZE_FINE = 0.25                        # 0.25 for scan, 0.5 for debug

# 3) Scan Settings
# ===================================================================
RF_amplitude_base = 2.50
U2_base = -0.35
E = [-0.07, +0.04, -0.01]

U2_to_scan = np.linspace(-0.20, -0.25, 11)
OUTSIDE_LOOP_REPEATS = 5
MAX_N_PEAKS = 5

# 3) Perform Experiments
# ===================================================================
results = {
    "meta": {
        "run_tag": RUN_TAG,
        "config": config,
        "RF_amplitude": float(RF_amplitude),
        "E": [float(x) for x in E],
        "U2_to_scan": U2_to_scan,
    },
    "runs": []
}

best_rows = []
Ex, Ey, Ez = E

initialize = True

for i, U2 in enumerate(U2_to_scan):

    print(f"[Manager] Taking data for U2 = {U2:.3f} ({i+1}/{len(U2_to_scan)}) ...")

    # Create the data structure for each U2
    u2_block = {
        "U2": float(U2),
        "rough_scan": None,
        "identified_lines": None,
        "fine_scans": [],
    }

    # Time estimation for rough scan
    time_est = (config["wait_time"] + config["load_time"] + LAG) * NO_OF_REPEATS_ROUGH * 200 * 1e-6

    # Rough Scan
    print(f"[Manager] Performing rough scan, estimated time cost: {time_est} s ...")
    scanner = (
        SingleParameterScan()
        .load_params(config)
        .set_param("RF_amplitude", RF_amplitude)
        .set_param("U2", U2)
        .set_param("Ex", Ex)
        .set_param("Ey", Ey)
        .set_param("Ez", Ez)
        .set_param("no_of_repeats", NO_OF_REPEATS_ROUGH)
        .set_param("histogram_refresh", NO_OF_REPEATS_ROUGH)
    )

    ts = run_with_422_relock(
        scanner, config,
        initialize=initialize,
        scanning_parameter = "tickle_frequency",
        min_scan = 1,
        max_scan = 200,
        steps = 200
    )
    initialize = False

    # Analyze the rough scan data
    fine_scans_to_run = analyze_rough_scan(ts, stepsize=STEPSIZE_FINE)

    # Store the rough scan data
    u2_block["rough_scan"] = {
        "timestamp": ts,
        "min_scan": 1,
        "max_scan": 200,
        "steps": 200,
    }
    u2_block["identified_lines"] = fine_scans_to_run

    # Create data structure for fine scans
    for line_id, fine_scan in enumerate(fine_scans_to_run):
        u2_block["fine_scans"].append({
            "line_id": line_id,
            "min_scan": fine_scan["min_scan"],
            "max_scan": fine_scan["max_scan"],
            "steps": fine_scan["steps"],
            "timestamps": [],
        })

    # Prepare for fine scans
    centers = [fine_scan["center"] for fine_scan in fine_scans_to_run]
    centers_str = ", ".join(f"{c:.1f}" for c in centers)
    print(f"[Manager] Identified {len(fine_scans_to_run)} lines: {centers_str} MHz")
    scanner.set_param("no_of_repeats", NO_OF_REPEATS_FINE)
    scanner.set_param("histogram_refresh", NO_OF_REPEATS_FINE)

    for rep in range(OUTSIDE_LOOP_REPEATS):

        for line_id, fine_scan in enumerate(fine_scans_to_run):

            time_est = (config["wait_time"] + config["load_time"] + LAG) * NO_OF_REPEATS_FINE * fine_scan["steps"] * 1e-6
            print(f"[Manager] Running repetition {rep} for line {line_id} at {fine_scan['center']:.1f} MHz "
                  f"({fine_scan['min_scan']:.1f} MHz, {fine_scan['max_scan']:.1f} MHz), estimated time cost {time_est} s ...")
            ts = run_with_422_relock(
                scanner, config,
                scanning_parameter = "tickle_frequency",
                min_scan = fine_scan["min_scan"],
                max_scan = fine_scan["max_scan"],
                steps = fine_scan["steps"]
            )

            # Analyze the fine scan data
            scan_result = analyze_fine_scan(
                ts,
                stepsize=STEPSIZE_FINE,
                scan_count=50,
                max_n_peaks=MAX_N_PEAKS,
                n_jobs=6,
            )

            out_prefix = get_fine_scan_prefix(ts, U2, RF_amplitude, line_id, rep)
            plot_fine_scan(ts, scan_result, out_prefix)

            # Store the fine scan data
            u2_block["fine_scans"][line_id]["timestamps"].append(ts)

            # Organize in-loop analyze result into csv
            for mode in ["lost", "trapped"]:
                best_fit = scan_result[mode]["best"]
                row = {
                    "timestamp": ts,
                    "mode": mode,
                    "U2": U2,
                    "RF_amplitude": RF_amplitude,
                    "line_id": line_id,
                    "rep": rep,
                    "min_scan": fine_scan["min_scan"],
                    "max_scan": fine_scan["max_scan"],
                }
                row.update(best_fit_to_row(best_fit, max_n_peaks=MAX_N_PEAKS))
                best_rows.append(row)

    results["runs"].append(u2_block)

with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
    json.dump(to_builtin(results), f, indent=2)

pd.DataFrame(best_rows).to_csv(SUMMARY_CSV, index=False)

print(f"[Manager] Saved summary: {SUMMARY_JSON}")
print(f"[Manager] Saved best-model CSV: {SUMMARY_CSV}")
