import numpy as np
import pandas as pd
import json
import random
from pathlib import Path
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

JOB_LIST_PATH = SAVE_DIR / "tickling_experiment_run_job_list.json"


def get_figure_dir(ts):
    date = ts.split("_")[0]
    fig_dir = SAVE_DIR / date
    fig_dir.mkdir(parents=True, exist_ok=True)
    return fig_dir


def get_scan_prefix(ts, RF_amplitude, U2, scan_type, setpoint_idx, rep):
    """scan_type: 'RF' or 'DC'. setpoint_idx and rep for unique filenames."""
    fig_dir = get_figure_dir(ts)
    prefix = fig_dir / f"{scan_type}_RF{RF_amplitude:.2f}_U2{U2:+.3f}_i{setpoint_idx:02d}_rep{rep:02d}_{ts}"
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


def load_or_init_job_list(
    rf_amplitude_list,
    u2_fixed_for_rf,
    u2_list,
    rf_fixed_for_dc,
    repeats,
    tickle_min,
    tickle_max,
    tickle_steps,
):
    """
    Load run_job_list from disk if exists; else create new and save.
    Returns (job_list, run_tag).
    """
    if JOB_LIST_PATH.exists():
        with open(JOB_LIST_PATH, "r", encoding="utf-8") as f:
            job_list = json.load(f)
        run_tag = job_list["run_tag"]
        print(f"[Manager] Resuming from existing job list: {JOB_LIST_PATH} (run_tag={run_tag})")
        return job_list, run_tag

    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_list = {
        "run_tag": run_tag,
        "repeats": repeats,
        "tickle_range": [tickle_min, tickle_max, tickle_steps],
        "RF": {
            "setpoints": [
                {
                    "RF_amplitude": float(rf_a),
                    "U2": float(u2_fixed_for_rf),
                    "done_count": 0,
                    "timestamps": [],
                }
                for rf_a in rf_amplitude_list
            ],
        },
        "DC": {
            "setpoints": [
                {
                    "RF_amplitude": float(rf_fixed_for_dc),
                    "U2": float(u2),
                    "done_count": 0,
                    "timestamps": [],
                }
                for u2 in u2_list
            ],
        },
    }
    with open(JOB_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(job_list, f, indent=2)
    print(f"[Manager] Created new job list: {JOB_LIST_PATH} (run_tag={run_tag})")
    return job_list, run_tag


def get_remaining_jobs_shuffled(job_list, scan_type, repeats):
    """
    Returns list of (setpoint_idx, rep) for jobs not yet done, shuffled.
    scan_type: "RF" or "DC".
    """
    setpoints = job_list[scan_type]["setpoints"]
    remaining = []
    for setpoint_idx, sp in enumerate(setpoints):
        done = sp["done_count"]
        for rep in range(done, repeats):
            remaining.append((setpoint_idx, rep))
    random.shuffle(remaining)
    return remaining


def save_job_list(job_list):
    with open(JOB_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(job_list, f, indent=2)


# 1) Global Settings
# ===================================================================
config = {
    "mode": "Trapping",
    "histogram_on": True,
    "bin_width": 1.0,
    "mesh_voltage": 130,
    "MCP_front": 500,
    "threshold_voltage": 60,
    "wait_time": 140,
    "load_time": 260,
    "frequency_390": 768.708843,
    "laser_failure": "raise error",
    "RF_on": True,
    "RF_amp_mode": "setpoint",
    "RF_frequency": 1.732,
    "ext_pulse_length": 900,
    "ext_pulse_level": 15.0,
    "U1": 0, "U3": 0, "U4": 0, "U5": 0,
    "tickle_on": True,
    "tickle_level": -10.0,
    "tickle_pulse_length": 130,
}

E = [-0.07, +0.04, -0.01]
Ex, Ey, Ez = E

# Single scan range (no rough/fine split); analysis uses fine-scan method
TICKLE_MIN = 20.0
TICKLE_MAX = 140.0
TICKLE_STEPS = 241
NO_OF_REPEATS = 20000
STEPSIZE_FINE = (TICKLE_MAX - TICKLE_MIN) / (TICKLE_STEPS - 1)
MAX_N_PEAKS = 8

# Repeats per setpoint (each point measured this many times)
REPEATS = 5


# 2) Scan Conditions: RF scan vs DC (U2) scan — logs kept separate
# ===================================================================
# RF scan: vary RF_amplitude, fixed U2
RF_amplitude_list = [
    -0.5, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6,
     1.8, 2.0, 2.2, 2.5, 3.0, 3.6, 4.3, 5.0, 6.0, 8.0,
]
U2_fixed_for_RF = -0.35

# DC scan: vary U2, fixed RF_amplitude
U2_list = [
    -0.200, -0.205, -0.210, -0.215, -0.220, -0.225, -0.230, -0.235,
    -0.240, -0.245, -0.250, -0.255, -0.260, -0.265, -0.270, -0.275,
    -0.280, -0.300, -0.320, -0.340, -0.360, -0.380, -0.400,
]
RF_fixed_for_DC = 1.50


# 3) Load or init run_job_list (enables resume)
# ===================================================================
job_list, RUN_TAG = load_or_init_job_list(
    RF_amplitude_list,
    U2_fixed_for_RF,
    U2_list,
    RF_fixed_for_DC,
    REPEATS,
    TICKLE_MIN,
    TICKLE_MAX,
    TICKLE_STEPS,
)

SUMMARY_JSON_RF = SAVE_DIR / f"run_summary_RF_{RUN_TAG}.json"
SUMMARY_CSV_RF = SAVE_DIR / f"run_best_models_RF_{RUN_TAG}.csv"
SUMMARY_JSON_DC = SAVE_DIR / f"run_summary_DC_{RUN_TAG}.json"
SUMMARY_CSV_DC = SAVE_DIR / f"run_best_models_DC_{RUN_TAG}.csv"

# Load existing results when resuming
results_RF = {
    "meta": {
        "run_tag": RUN_TAG,
        "scan_type": "RF",
        "config": config,
        "E": [float(x) for x in E],
        "U2_fixed": float(U2_fixed_for_RF),
        "RF_amplitude_list": list(RF_amplitude_list),
        "tickle_range": [TICKLE_MIN, TICKLE_MAX, TICKLE_STEPS],
        "repeats": REPEATS,
    },
    "runs": [],
}
best_rows_RF = []
if SUMMARY_JSON_RF.exists():
    with open(SUMMARY_JSON_RF, "r", encoding="utf-8") as f:
        results_RF = json.load(f)
if SUMMARY_CSV_RF.exists():
    best_rows_RF = pd.read_csv(SUMMARY_CSV_RF).to_dict("records")

results_DC = {
    "meta": {
        "run_tag": RUN_TAG,
        "scan_type": "DC",
        "config": config,
        "E": [float(x) for x in E],
        "RF_amplitude_fixed": float(RF_fixed_for_DC),
        "U2_list": list(U2_list),
        "tickle_range": [TICKLE_MIN, TICKLE_MAX, TICKLE_STEPS],
        "repeats": REPEATS,
    },
    "runs": [],
}
best_rows_DC = []
if SUMMARY_JSON_DC.exists():
    with open(SUMMARY_JSON_DC, "r", encoding="utf-8") as f:
        results_DC = json.load(f)
if SUMMARY_CSV_DC.exists():
    best_rows_DC = pd.read_csv(SUMMARY_CSV_DC).to_dict("records")


# 4) Run RF scans (shuffled order, one instance log)
# ===================================================================
remaining_RF = get_remaining_jobs_shuffled(job_list, "RF", REPEATS)
if remaining_RF:
    scanner_RF = (
        SingleParameterScan(comment="tickling_experiment_RF")
        .load_params(config)
        .set_param("U2", U2_fixed_for_RF)
        .set_param("Ex", Ex)
        .set_param("Ey", Ey)
        .set_param("Ez", Ez)
        .set_param("no_of_repeats", NO_OF_REPEATS)
        .set_param("histogram_refresh", NO_OF_REPEATS)
    )
    initialize = True
    total_rf = len(remaining_RF)
    for run_idx, (setpoint_idx, rep) in enumerate(remaining_RF):
        sp = job_list["RF"]["setpoints"][setpoint_idx]
        RF_amplitude = sp["RF_amplitude"]
        U2 = sp["U2"]
        print(f"[Manager] RF scan ({run_idx+1}/{total_rf}) setpoint_i={setpoint_idx} rep={rep} "
              f"RF_amplitude={RF_amplitude:.2f} U2={U2:.3f} ...")

        scanner_RF.set_param("RF_amplitude", RF_amplitude)

        ts = run_with_422_relock(
            scanner_RF, config,
            initialize=initialize,
            scanning_parameter="tickle_frequency",
            min_scan=TICKLE_MIN,
            max_scan=TICKLE_MAX,
            steps=TICKLE_STEPS,
        )
        initialize = False

        scan_result = analyze_fine_scan(
            ts,
            stepsize=STEPSIZE_FINE,
            scan_count=121,
            max_n_peaks=MAX_N_PEAKS,
            n_jobs=6,
        )

        out_prefix = get_scan_prefix(ts, RF_amplitude, U2, "RF", setpoint_idx, rep)
        plot_fine_scan(ts, scan_result, str(out_prefix))

        results_RF["runs"].append({
            "RF_amplitude": float(RF_amplitude),
            "U2": float(U2),
            "setpoint_idx": setpoint_idx,
            "rep": rep,
            "timestamp": ts,
            "min_scan": TICKLE_MIN,
            "max_scan": TICKLE_MAX,
            "steps": TICKLE_STEPS,
        })

        for mode in ["lost", "trapped"]:
            best_fit = scan_result[mode]["best"]
            row = {
                "timestamp": ts,
                "mode": mode,
                "RF_amplitude": RF_amplitude,
                "U2": U2,
                "scan_type": "RF",
                "setpoint_idx": setpoint_idx,
                "rep": rep,
                "min_scan": TICKLE_MIN,
                "max_scan": TICKLE_MAX,
            }
            row.update(best_fit_to_row(best_fit, max_n_peaks=MAX_N_PEAKS))
            best_rows_RF.append(row)

        job_list["RF"]["setpoints"][setpoint_idx]["done_count"] = rep + 1
        job_list["RF"]["setpoints"][setpoint_idx]["timestamps"].append(ts)
        save_job_list(job_list)
        with open(SUMMARY_JSON_RF, "w", encoding="utf-8") as f:
            json.dump(to_builtin(results_RF), f, indent=2)
        pd.DataFrame(best_rows_RF).to_csv(SUMMARY_CSV_RF, index=False)

    print(f"[Manager] Saved RF summary: {SUMMARY_JSON_RF}")
else:
    print(f"[Manager] RF section: no remaining jobs (already complete).")


# 5) Run DC (U2) scans (shuffled order, one instance log)
# ===================================================================
remaining_DC = get_remaining_jobs_shuffled(job_list, "DC", REPEATS)
if remaining_DC:
    scanner_DC = (
        SingleParameterScan(comment="tickling_experiment_DC")
        .load_params(config)
        .set_param("RF_amplitude", RF_fixed_for_DC)
        .set_param("Ex", Ex)
        .set_param("Ey", Ey)
        .set_param("Ez", Ez)
        .set_param("no_of_repeats", NO_OF_REPEATS)
        .set_param("histogram_refresh", NO_OF_REPEATS)
    )
    total_dc = len(remaining_DC)
    for run_idx, (setpoint_idx, rep) in enumerate(remaining_DC):
        sp = job_list["DC"]["setpoints"][setpoint_idx]
        RF_amplitude = sp["RF_amplitude"]
        U2 = sp["U2"]
        print(f"[Manager] DC scan ({run_idx+1}/{total_dc}) setpoint_i={setpoint_idx} rep={rep} "
              f"U2={U2:.3f} RF_amplitude={RF_amplitude:.2f} ...")

        scanner_DC.set_param("U2", U2)

        ts = run_with_422_relock(
            scanner_DC, config,
            initialize=False,
            scanning_parameter="tickle_frequency",
            min_scan=TICKLE_MIN,
            max_scan=TICKLE_MAX,
            steps=TICKLE_STEPS,
        )

        scan_result = analyze_fine_scan(
            ts,
            stepsize=STEPSIZE_FINE,
            scan_count=121,
            max_n_peaks=MAX_N_PEAKS,
            n_jobs=6,
        )

        out_prefix = get_scan_prefix(ts, RF_amplitude, U2, "DC", setpoint_idx, rep)
        plot_fine_scan(ts, scan_result, str(out_prefix))

        results_DC["runs"].append({
            "RF_amplitude": float(RF_amplitude),
            "U2": float(U2),
            "setpoint_idx": setpoint_idx,
            "rep": rep,
            "timestamp": ts,
            "min_scan": TICKLE_MIN,
            "max_scan": TICKLE_MAX,
            "steps": TICKLE_STEPS,
        })

        for mode in ["lost", "trapped"]:
            best_fit = scan_result[mode]["best"]
            row = {
                "timestamp": ts,
                "mode": mode,
                "RF_amplitude": RF_amplitude,
                "U2": U2,
                "scan_type": "DC",
                "setpoint_idx": setpoint_idx,
                "rep": rep,
                "min_scan": TICKLE_MIN,
                "max_scan": TICKLE_MAX,
            }
            row.update(best_fit_to_row(best_fit, max_n_peaks=MAX_N_PEAKS))
            best_rows_DC.append(row)

        job_list["DC"]["setpoints"][setpoint_idx]["done_count"] = rep + 1
        job_list["DC"]["setpoints"][setpoint_idx]["timestamps"].append(ts)
        save_job_list(job_list)
        with open(SUMMARY_JSON_DC, "w", encoding="utf-8") as f:
            json.dump(to_builtin(results_DC), f, indent=2)
        pd.DataFrame(best_rows_DC).to_csv(SUMMARY_CSV_DC, index=False)

    print(f"[Manager] Saved DC summary: {SUMMARY_JSON_DC}")
else:
    print(f"[Manager] DC section: no remaining jobs (already complete).")
