import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def load_data(timestamp, ynames = ["ratio_signal"]):
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

def find_optima(timestamp: str, yname: str = "ratio_signal") -> float:
    # Read data
    xs, ys = load_data(timestamp, [yname])
    return xs[ys[yname].argmax()]

def dummy_fine_scan_range():
    return -0.4, 0.2, 61

def dummy_optima():
    return -0.13

def find_peaks_and_plot(x, y, noise):

    peaks = find_peaks(y, height=6*noise, prominence=3*noise)

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

def analyze_rough_scan(timestamp):

    # Extract Data
    x, ys = load_data(timestamp, ynames = ["ratio_signal", "ratio_lost"])
    y1 = -ys["ratio_signal"]
    y2 = ys["ratio_lost"]

    # Normalize Data
    baseline1 = np.sort(y1)[:int(len(y1)*0.25)].mean()
    baseline2 = np.sort(y2)[:int(len(y2)*0.25)].mean()
    peak1 = np.max(y1)
    peak2 = np.max(y2)
    y_trapped = (y1 - baseline1) / (peak1 - baseline1)
    y_lost = (y2 - baseline2) / (peak2 - baseline2)

    # Noise Level
    noise_trapped = np.sort(y_trapped)[:int(len(y_trapped)*0.25)].std()
    noise_lost = np.sort(y_lost)[:int(len(y_lost)*0.25)].std()

    # Peak Search
    peaks_trapped = find_peaks(
        y_trapped,
        height=max(6*noise_trapped, 0.15),
        prominence=max(3*noise_trapped, 0.10),
    )
    peaks_lost = find_peaks(
        y_lost,
        height=max(6*noise_lost, 0.15),
        prominence=max(3*noise_lost, 0.10),
    )

    # Construct Fine Scan Ranges
    fine_scans_trapped = construct_scan_ranges(x, y_trapped, peaks_trapped)
    fine_scans_lost = construct_scan_ranges(x, y_lost, peaks_lost)

    fine_scans = merge_scan_ranges(fine_scans_trapped, fine_scans_lost, x, y_trapped, y_lost)

    return fine_scans

def _extract_mus_from_popt(popt, n_peaks):
    # popt = [c0, amp1, mu1, sigma1, amp2, mu2, sigma2, ...]
    mus = []
    for i in range(n_peaks):
        mus.append(float(popt[1 + 3*i + 1]))
    return mus

def analyze_fine_scan(timestamp, stepsize=0.2, r2_gate=0.90, scan_count=50, max_n_peaks=4):

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
                scan_count=scan_count
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
            ax.legend(True, linestyle="--", alpha=0.6)
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

# Fitting Helpers
# ===============================================
def fit_n_peaks(x, y, n_peaks, mode, stepsize, init_mus, scan_count=50, max_nfev=20000):
    """
    Fit data with n_peaks of gaussian peaks, inital value of n_peaks-1 peaks are fixed.
    The fitter will generate scan_count initial values of the new peak and fit for each of them.
    The fitting with highest U2 will be picked for the best model.
    Return: parameters of the best fitting, R2 and AICc of the best fitting
    """

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_min, x_max = np.min(x), np.max(x)

    c0 = baseline_guess(y, mode)
    sigma0 = sigma_guess(x, stepsize)

    if (n_peaks - len(init_mus)) == 1:
        mu0_to_scan = [(mu0,) for mu0 in np.linspace(x_min, x_max, scan_count)]
    elif (n_peaks - len(init_mus)) == 0:
        mu0_to_scan = [()]
    else:
        raise ValueError("Not Supported!")

    bounds = build_bounds(n_peaks, x_min, x_max, stepsize, mode)

    history = []
    best = None

    for mu0_tuple in mu0_to_scan:
        mu0s = init_mus + list(mu0_tuple)

        p0 = [c0]
        for mu in mu0s:
            p0.append(amp_guess_at_mu(x, y, mu, c0, mode))
            p0.append(mu)
            p0.append(sigma0)

        try:
            popt, pcov = curve_fit(
                gaussian_sum, x, y,
                p0=p0, bounds=bounds,
                max_nfev=max_nfev
            )
            yhat = gaussian_sum(x, *popt)
            r2 = calculate_r2(y, yhat)
            k = 1 + 3 * n_peaks
            aicc = calculate_aicc(y, yhat, k)

            entry = {
                "n_peaks": int(n_peaks),
                "mu0": mu0s,
                "popt": popt,
                "pcov": pcov,
                "r2": r2,
                "aicc": aicc,
                "ok": True,
            }

        except Exception as e:
            entry = {
                "n_peaks": int(n_peaks),
                "mu0": mu0s,
                "popt": None,
                "pcov": None,
                "r2": -np.inf,
                "aicc": np.inf,
                "ok": False,
                "err": str(e)
            }
        
        history.append(entry)

        if entry["ok"]:
            if (best is None) or (entry["r2"] > best["r2"]):
                best = entry

    return best, history

def gaussian(x, amp, mu, sigma):
    return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def gaussian_sum(x, *params):
    # params = [c0, amp1, mu1, sigma1, amp1, mu2, sigma2, ...]

    c0 = params[0]
    y = 0.0 * x + c0

    for i in range((len(params) - 1) // 3):
        amp   = params[1 + 3*i]
        mu    = params[1 + 3*i + 1]
        sigma = params[1 + 3*i + 2]
        y += gaussian(x, amp, mu, sigma)

    return y

def calculate_r2(y, yhat):

    y = np.asarray(y)
    yhat = np.asarray(yhat)

    sse = np.sum((y - yhat) ** 2)
    sst = np.sum((y - np.mean(y)) ** 2)
    if sst <= 0:
        return 0.0
    
    return 1.0 - sse / sst

def calculate_aicc(y, yhat, k):

    y = np.asarray(y)
    yhat = np.asarray(yhat)

    n = y.size
    rss = np.sum((y - yhat) ** 2)

    # Avoid log(0)
    rss = max(float(rss), 1e-300)

    aic = n * np.log(rss / n) + 2 * k
    if n <= (k + 1):
        return np.inf
    
    return aic + (2 * k * (k + 1)) / (n - k - 1)

def baseline_guess(y, mode):

    y = np.asarray(y)
    quantile = max(1, round(0.25 * len(y)))

    if mode == "lost":
        return float(np.sort(y)[:quantile].mean())
    elif mode == "trapped":
        return float(np.sort(y)[-quantile:].mean())

def primary_center_guess(x, y, mode):
    
    x = np.asarray(x)
    y = np.asarray(y)

    if mode == "lost":
        return float(x[np.argmax(y)])
    elif mode == "trapped":
        return float(x[np.argmin(y)])

def amp_guess_at_mu(x, y, mu, c0, mode):

    index = np.argmin(np.abs(x-mu))
    a = y[index] - c0

    if mode == "lost":
        return max(a, 1e-3)
    elif mode == "trapped":
        return min(a, -1e-3)

def sigma_guess(x, stepsize):
    span = np.max(x) - np.min(x)
    return max(span / 20.0, 2.0 * stepsize, 0.5)

def build_bounds(n_peaks, x_min, x_max, stepsize, mode):

    # Baseline c0 bounds
    lower_bound = [-np.inf]
    upper_bound = [ np.inf]

    if mode == "lost":
        amp_low, amp_high = 0.0, np.inf
    elif mode == "trapped":
        amp_low, amp_high = -np.inf, 0.0

    sigma_low = max(stepsize, 1e-3)

    # Gaussian parameters bounds
    for _ in range(n_peaks):
        lower_bound += [amp_low, -np.inf, sigma_low]
        upper_bound += [amp_high, np.inf, np.inf]

    return (lower_bound, upper_bound)
