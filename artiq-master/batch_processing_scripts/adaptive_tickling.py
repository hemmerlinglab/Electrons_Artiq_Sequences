from artiq_controller import SingleParameterScan

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from helper_functions import analyze_rough_scan

# 1) Meta Settings
# ===================================================================
save_path = "/home/electrons/software/data/"

# 2) Global Settings
# ===================================================================
config = {
    "mode": "Trapping",
    "histogram_on": True,
    "bin_width": 1.0,
    #"histogram_refresh": 16000,
    "mesh_voltage": 120,                    # unit: V
    "MCP_front": 400,                       # unit: V
    "threshold_voltage": 60,                # unit: mV
    "wait_time": 90,                        # unit: us
    "load_time": 210,                       # unit: us
    "trap": "Single PCB",
    "flip_electrodes": False,
    "frequency_422": 709.076990,            # unit: THz
    "frequency_390": 768.708843,            # unit: THz
    "RF_on": True,
    "RF_amp_mode": "setpoint",
    "RF_frequency": 1.732,                  # unit: GHz
    "ext_pulse_length": 900,                # unit: ns
    "ext_pulse_level": 15.0,                # unit: V (Vpp)
    "U1": 0, "U3": 0, "U4": 0, "U5": 0,     # unit: V/m^2
    "tickle_on": True,
    "tickle_level": -10.0,                  # unit: MHz
    "tickle_pulse_length": 80,              # unit: us
    #"no_of_repeats": 16000
}

LAG = 250                                   # unit: us
NO_OF_REPEATS_ROUGH = 6000
NO_OF_REPEATS_FINE = 20000

# 3) Scan Settings
# ===================================================================
RF_amplitude = 4.50
E = [-0.166, 0.024, 0.04]

U2_to_scan = np.linspace(-0.20, -0.25, 11)
OUTSIDE_LOOP_REPEATS = 5

# 4) Perform Experiments
# ===================================================================
results = {
    "meta": {
        "config": config,
        "RF_amplitude": float(RF_amplitude),
        "E": [float(x) for x in E],
        "U2_to_scan": U2_to_scan,
    },
    "runs": []
}

Ex, Ey, Ez = E

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

    ts = scanner.run(
        scanning_parameter = "tickle_frequency",
        min_scan = 1,
        max_scan = 200,
        steps = 200
    )

    # Analyze the rough scan data
    fine_scans_to_run = analyze_rough_scan(ts)

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
    centers = [fine_scan["center"] for fs in fine_scans_to_run]
    print(f"[Manager] Identified {len(fine_scans_to_run)} lines: {", ".join(f'{c:.1f}' for c in centers)} MHz")
    scanner.set_param("no_of_repeats": NO_OF_REPEATS_FINE)
    scanner.set_param("histogram_refresh", NO_OF_REPEATS_FINE)

    for rep in range(OUTSIDE_LOOP_REPEATS):

        for line_id, fine_scan in enumerate(fine_scans_to_run):

            time_est = (config["wait_time"] + config["load_time"] + LAG) * NO_OF_REPEATS_FINE * fine_scan["steps"] * 1e-6
            print(f"[Manager] Running repetition {rep} for line {line_id} ({fine_scans_to_run['centers'][line_id]:.1f} MHz), estimated time cost {time_est} s ...")
            ts = scanner.run(
                scanning_parameter = "tickle_frequency",
                min_scan = fine_scan["min_scan"],
                max_scan = fine_scan["max_scan"],
                steps = fine_scan["steps"]
            )

            # Analyze the fine scan data

            # Store the fine scan data
            u2_block["fine_scans"][line_id]["timestamps"].append(ts)

    results["runs"].append(u2_block)



