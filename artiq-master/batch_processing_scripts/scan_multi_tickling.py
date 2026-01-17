from artiq_controller import SingleParameterScan

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 1) Meta Settings
# ===================================================================
save_path = "/home/electrons/software/data/"

# 2) Global Settings
# ===================================================================
config = {
    "histogram_on": True,
    "bin_width": 1.0,
    "histogram_refresh": 16000,
    "mesh_voltage": 120,
    "MCP_front": 400,
    "threshold_voltage": 60,
    "wait_time": 90,
    "load_time": 210,
    "trap": "Single PCB",
    "flip_electrodes": False,
    "frequency_422": 709.079965,
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
    "no_of_repeats": 16000
}

# 3) Scan Settings
# ===================================================================
RF_amplitude = 2.50
U2 = -0.38
E = [-0.166, 0.024, 0.04]

scan_ranges = [
    [25, 42],
    [46, 58],
    [78, 94],
    [112, 130],
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

def plot_data(xs, ys1, ys2):

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))

    ax1.plot(xs, ys1)
    ax1.set_xlabel("tickle_frequency (MHz)")
    ax1.set_ylabel("trapped ratio")

    ax2.plot(xs, ys2)
    ax2.set_xlabel("tickle_frequency (MHz)")
    ax2.set_ylabel("lostratio")

    return fig, (ax1, ax2)

# 5) Perform Experiments
# ===================================================================
experiment_list = []

time_est = 0
for ran in scan_ranges:
    steps = (ran[1] - ran[0]) / 0.2 + 1
    time_est += steps * 8

print(f"[Manage] Estimated time cost: {time_est} s")

for i, current_range in enumerate(scan_ranges):

    Ex, Ey, Ez = E

    print(f"[Manager] Step {i+1}/{len(scan_ranges)}: [{current_range[0]:.0f}, {current_range[1]:.0f}] ...")

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
        min_scan = current_range[0],
        max_scan = current_range[1],
        steps = (current_range[1] - current_range[0]) / 0.2 + 1
    )

    experiment_list.append({"scan_range": current_range, "exp_no": ts})
    print(f"[Manager] Experiment Timestamp: {ts}")

    x, y1, y2 = load_data(ts)
    fig, _ = plot_data(x, y1, y2)
    fig.savefig(f"{ts}.png", dpi=300)
