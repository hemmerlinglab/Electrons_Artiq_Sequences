import numpy as np
from scipy.signal import find_peaks
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fitting_functions import find_peaks, gaussian_sum

# Utility Functions - Load_data
# ===============================================

def load_data(timestamp, ynames = ["ratio_signal"]):

    print(f"[Data Loader] loading timestamp: {timestamp} ...")

    date, _ = timestamp.split("_")
    basefilename = f"/home/electrons/software/data/{date}/{timestamp}"
    xdata = np.genfromtxt(f"{basefilename}_arr_of_setpoints")
    ydata = {}
    for yname in ynames:
        ydata[yname] = np.genfromtxt(f"{basefilename}_{yname}")
    return xdata, ydata

def load_configuration(timestamp, conf_names=["U2"]):
    date, _ = timestamp.split("_")
    filename = f"/home/electrons/software/data/{date}/{timestamp}_conf"

    with open(filename) as f:
        lines = [line.strip() for line in f]

    config_map = {
        lines[i].strip("[]"): lines[i+1].split("=", 1)[1].strip()
        for i in range(len(lines) - 1)
        if lines[i].startswith("[") and lines[i+1].startswith("val =")
    }

    return [config_map.get(name, "") for name in conf_names]

def calculate_fine_scan_range(timestamp: str, yname: str = "ratio_signal", stepsize: float = 0.01):
    # Read data
    xs, ys_dict = load_data(timestamp, [yname])
    ys = ys_dict[yname]

    # Calculate range
    maxval = np.max(ys)
    mask = ys > (maxval / 2.0)
    xs_in = xs[mask]
    xmin, xmax = np.min(xs_in), np.max(xs_in)
    steps = int(round((xmax - xmin) / stepsize)) + 1
    return xmin, xmax, steps

def moving_average(y, window=7):
    y = np.asarray(y)
    if window is None or window <= 1:
        return y
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(y, kernel, mode="same")

def find_best_laser_frequency(timestamp):
    x, y = load_data(timestamp, ynames=["loading_signal"])
    y_smooth = moving_average(y["loading_signal"])
    return float(x[np.argmax(y_smooth)])

def analyze_rough_scan(timestamp, stepsize=0.2):

    # Extract Data
    x, ys = load_data(timestamp, ynames = ["ratio_signal", "ratio_lost"])
    y1 = -ys["ratio_signal"]
    y2 = ys["ratio_lost"]
    dx = x[1] - x[0]
    min_distance = int(np.ceil(5.0 / max(abs(dx), 1e-3)))

    # Normalize Data
    baseline1 = np.sort(y1)[:int(len(y1)*0.25)].mean()
    baseline2 = np.sort(y2)[:int(len(y2)*0.25)].mean()
    peak1 = np.max(y1)
    peak2 = np.max(y2)
    y_trapped = (y1 - baseline1) / (peak1 - baseline1)
    y_lost = (y2 - baseline2) / (peak2 - baseline2)

    # Noise Level
    noise_trapped = y_trapped[x > 150].std()
    noise_lost = y_lost[x > 150].std()

    # Peak Search
    peaks_trapped = find_peaks(
        y_trapped,
        height=max(6*noise_trapped, 0.20),
        prominence=max(3*noise_trapped, 0.15),
        distance=min_distance,
    )
    peaks_lost = find_peaks(
        y_lost,
        height=max(6*noise_lost, 0.20),
        prominence=max(3*noise_lost, 0.15),
        distance=min_distance,
    )

    # Construct Fine Scan Ranges
    fine_scans_trapped = construct_scan_ranges(x, y_trapped, peaks_trapped, stepsize=stepsize)
    fine_scans_lost = construct_scan_ranges(x, y_lost, peaks_lost, stepsize=stepsize)

    fine_scans = merge_scan_ranges(fine_scans_trapped, fine_scans_lost, x, y_trapped, y_lost, stepsize=stepsize)

    return fine_scans

def analyze_fine_scan(timestamp, stepsize=0.2, r2_gate=0.90, scan_count=50, max_n_peaks=4, n_jobs=1):

    modes = ["lost", "trapped"]
    x, ys = load_data(timestamp, ynames = ["ratio_signal", "ratio_lost"])

    y = {"lost": ys["ratio_lost"], "trapped": ys["ratio_signal"]}
    result = {}

    for mode in modes:
        result[mode] = {"best": None, "all": []}
        n_peaks = 1

        # Generate initial guess of mu0
        if mode == "lost":
            mu0 = [float(x[np.argmax(y[mode])])]
        elif mode == "trapped":
            mu0 = [float(x[np.argmin(y[mode])])]

        while (n_peaks <= max_n_peaks):
            result_n_peaks, _ = fit_n_peaks(
                x, y[mode], n_peaks, mode,
                stepsize=stepsize,
                init_mus=mu0,
                scan_count=scan_count,
                n_jobs=n_jobs,
            )

            if result_n_peaks is None:
                print(f"[Analyze Fine Scan] Fitting for experiment {timestamp} is failed at n_peaks = {n_peaks}")
                break

            result[mode]["all"].append(result_n_peaks)
            if (result[mode]["best"] is None) or (result_n_peaks["aicc"] < result[mode]["best"]["aicc"]):
                result[mode]["best"] = result_n_peaks

            if result_n_peaks["r2"] > r2_gate:
                break
            if (n_peaks >= 2) and (result_n_peaks["aicc"] > result[mode]["best"]["aicc"]):
                break

            mu0 = _extract_mus_from_popt(result_n_peaks["popt"], n_peaks)
            n_peaks += 1
    
    return result

def plot_fine_scan(timestamp, fit_result, out_name):

    modes = ["lost", "trapped"]
    x, ys = load_data(timestamp, ynames = ["ratio_signal", "ratio_lost"])
    u2 = float(load_configuration(timestamp, conf_names=["U2"])[0])

    y = {"lost": ys["ratio_lost"], "trapped": ys["ratio_signal"]}

    fig, axs = plt.subplots(2, 1, figsize=(12, 12), sharex=True)
    axes = {"lost": axs[0], "trapped": axs[1]}

    for mode in modes:

        ax = axes[mode]

        best_fit = fit_result[mode].get("best", None)
        if (best_fit is None) or (not best_fit.get("ok", False)):
            ax.scatter(x, y[mode], label="data")
            ax.set_title(f"{timestamp}: U2 = {u2:.3f} ({mode}) - [NO FIT]")
            ax.set_ylabel(f"{mode} count / loading count")
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.legend()
            continue

        popt = best_fit["popt"]
        n_peaks = best_fit["n_peaks"]

        xfit = np.linspace(np.min(x), np.max(x), 1000)
        yfit = gaussian_sum(xfit, *popt)

        ax.scatter(x, y[mode], label="data")
        ax.plot(xfit, yfit, label=f"fitting with {n_peaks} peaks")

        ax.set_title(f"{timestamp}: U2 = {u2:.3f} ({mode})")
        ax.set_ylabel(f"{mode} count / loading count")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend()

    axes["trapped"].set_xlabel("Tickle Frequency (MHz)")
    fig.savefig(f"{out_name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"[Plot] Saved: {out_name}.png")

# Analyze Rough Scan Helpers
# ===============================================
def find_peaks_and_plot(x, y, noise):

    peaks = find_peaks(y, height=max(6*noise, 0.20), prominence=max(3*noise, 0.15), distance=5)

    plt.plot(x, y)
    plt.axhline(y=6*noise, linestyle="--")
    for pk in peaks[0]:
        plt.axvline(x=x[pk], linestyle="--")
    plt.show()

    return peaks

def construct_scan_ranges(x, y, peaks, width=10.0, stepsize=0.2):

    # Create Ranges
    if isinstance(peaks, tuple): peaks = peaks[0]
    peaks = np.asarray(peaks, dtype=int)
    if peaks.size == 0: return []
    centers = np.sort(x[peaks])
    ranges = [(max(c - width, 1.0), min(c + width, 200.0)) for c in centers]

    # Merge Intersecting Ranges
    merged = []
    current_low, current_high = ranges[0]
    for low, high in ranges[1:]:
        if low <= current_high:
            current_high = max(current_high, high)
        else:
            merged.append((current_low, current_high))
            current_low, current_high = low, high
    merged.append((current_low, current_high))

    # Define Fine Scans
    fine_scans = []

    for low, high in merged:
        fine_scan = {}

        fine_scan["min_scan"] = low
        fine_scan["max_scan"] = high

        mask = (x > low) & (x < high)
        current_x = x[mask]
        current_y = y[mask]
        fine_scan["center"] = current_x[np.argmax(current_y)]

        fine_scan["steps"] = round((high - low) / stepsize) + 1
        fine_scans.append(fine_scan)

    return fine_scans

def merge_scan_ranges(fine_scans_trapped, fine_scans_lost, x, y_trapped, y_lost, stepsize=0.2):

    # Collect all ranges with a lost-flag (internal only)
    intervals = []
    for s in fine_scans_trapped:
        intervals.append((float(s["min_scan"]), float(s["max_scan"]), False))
    for s in fine_scans_lost:
        intervals.append((float(s["min_scan"]), float(s["max_scan"]), True))

    if len(intervals) == 0:
        return []

    # Sort by low edge
    intervals.sort(key=lambda t: t[0])

    # Merge intersecting/touching ranges, keep whether any lost-range participated
    merged = []
    current_low, current_high, current_has_lost = intervals[0]
    for low, high, has_lost in intervals[1:]:
        if low <= current_high:
            current_high = max(current_high, high)
            current_has_lost = current_has_lost or has_lost
        else:
            merged.append((current_low, current_high, current_has_lost))
            current_low, current_high, current_has_lost = low, high, has_lost
    merged.append((current_low, current_high, current_has_lost))

    # Decide centers and steps
    x = np.asarray(x)
    y_trapped = np.asarray(y_trapped)
    y_lost = np.asarray(y_lost)

    fine_scans = []

    for low, high, has_lost in merged:
        fine_scan = {}
        fine_scan["min_scan"] = low
        fine_scan["max_scan"] = high

        mask = (x > low) & (x < high)

        if np.any(mask):
            current_x = x[mask]
            if has_lost:
                current_y = y_lost[mask]
            else:
                current_y = y_trapped[mask]
            fine_scan["center"] = float(current_x[np.argmax(current_y)])
        else:
            fine_scan["center"] = float(0.5 * (low + high))

        fine_scan["steps"] = int(round((high - low) / stepsize)) + 1
        fine_scans.append(fine_scan)

    return fine_scans
