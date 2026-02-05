import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/artiq_controller")
from artiq_controller import SingleParameterScan

# 1) Meta Settings
# ===================================================================
save_path = "/home/electrons/software/data/"

# 2) Global Settings
# ===================================================================
config = {
    "histogram_on": True,
    "bin_width": 1.0,
    "histogram_refresh": 3000,
    "mesh_voltage": 120,
    "MCP_front": 400,
    "threshold_voltage": 60,
    "wait_time": 90,
    "load_time": 210,
    "trap": "Single PCB",
    "flip_electrodes": False,
    "frequency_422": 709.076740,
    "frequency_390": 768.708843,
    "RF_on": True,
    "RF_amp_mode": "setpoint",
    "RF_frequency": 1.732,
    "ext_pulse_length": 900,
    "ext_pulse_level": 15.0,
    "U1": 0, "U3": 0, "U4": 0, "U5": 0,
    "tickle_on": True,
    "tickle_level": -10.0,
    "tickle_pulse_length": 80,
    "no_of_repeats": 3000
}

# 3) Scan Settings
# =================================================================
RF_amplitude = 2.50
U2 = -0.225

scan_range = [30, 110]
steps = 81

trial_E = [
    [-0.17, 0.03, -0.01],
    [-0.17, 0.05, -0.01],
    [-0.17, 0.07, -0.01],
    [-0.17, 0.03, 0.01],
    [-0.17, 0.05, 0.01],
    [-0.17, 0.07, 0.01],
    [-0.17, 0.03, 0.03],
    [-0.17, 0.05, 0.03],
    [-0.17, 0.07, 0.03],
    [-0.17, 0.03, 0.05],
    [-0.17, 0.05, 0.05],
    [-0.17, 0.07, 0.05],
    [-0.17, 0.03, 0.07],
    [-0.17, 0.05, 0.07],
    [-0.17, 0.07, 0.07],
    [-0.2, 0.03, -0.01],
    [-0.2, 0.05, -0.01],
    [-0.2, 0.07, -0.01],
    [-0.2, 0.03, 0.01],
    [-0.2, 0.05, 0.01],
    [-0.2, 0.07, 0.01],
    [-0.2, 0.03, 0.03],
    [-0.2, 0.05, 0.03],
    [-0.2, 0.07, 0.03],
    [-0.2, 0.03, 0.05],
    [-0.2, 0.05, 0.05],
    [-0.2, 0.07, 0.05],
    [-0.2, 0.03, 0.07],
    [-0.2, 0.05, 0.07],
    [-0.2, 0.07, 0.07],
    [-0.23, 0.03, -0.01],
    [-0.23, 0.05, -0.01],
    [-0.23, 0.07, -0.01],
    [-0.23, 0.03, 0.01],
    [-0.23, 0.05, 0.01],
    [-0.23, 0.07, 0.01],
    [-0.23, 0.03, 0.03],
    [-0.23, 0.05, 0.03],
    [-0.23, 0.07, 0.03],
    [-0.23, 0.03, 0.05],
    [-0.23, 0.05, 0.05],
    [-0.23, 0.07, 0.05],
    [-0.23, 0.03, 0.07],
    [-0.23, 0.05, 0.07],
    [-0.23, 0.07, 0.07],
]

# 4) Plot Functions
# ===================================================================
def load_data(ts):

    basepath = '/home/electrons/software/data/'
    date, _ = ts.split("_")
    basefilename = f"{basepath}/{date}/{ts}"

    xs = np.genfromtxt(f"{basefilename}_arr_of_setpoints", delimiter=",")
    ys1 = np.genfromtxt(f"{basefilename}_ratio_signal", delimiter=",")
    ys2 = np.genfromtxt(f"{basefilename}_ratio_lost", delimiter=",")

    return xs, ys1, ys2

def plot_data(xs, ys1, ys2, efield):

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    fig.suptitle(f"E = [{efield[0]:.2f}, {efield[1]:.2f}, {efield[2]:.2f}]")

    ax1.plot(xs, ys1)
    ax1.set_xlabel("tickle_frequency (MHz)")
    ax1.set_ylabel("trapped ratio")

    ax2.plot(xs, ys2)
    ax2.set_xlabel("tickle_frequency (MHz)")
    ax2.set_ylabel("lost ratio")

    return fig, (ax1, ax2)

# 5) Perform Experiments
# ===================================================================
experiment_list = []

time_est = steps * len(trial_E) * 2
print(f"[Manage] Estimated time cost: {time_est} s")

for i, efield in enumerate(trial_E):

    Ex, Ey, Ez = efield

    print(f"[Manager] Step {i+1}/{len(trial_E)}: E = [{Ex:.3f}, {Ey:.3f}, {Ez:.3f}] ...")

    # Perform scan
    scanner = (
        SingleParameterScan()
        .load_params(config)
        .set_param("RF_amplitude", RF_amplitude)
        .set_param("U2", U2)
        .set_param("Ex", Ex)
        .set_param("Ey", Ey)
        .set_param("Ez", Ez)
    )

    ts = scanner.run(
        scanning_parameter = "tickle_frequency",
        min_scan = scan_range[0],
        max_scan = scan_range[1],
        steps = steps
    )

    experiment_list.append({"E": efield, "exp_no": ts})

    x, y1, y2 = load_data(ts)
    fig, _ = plot_data(x, y1, y2, efield)
    fig.savefig(f"{ts}.png", dpi=300)
