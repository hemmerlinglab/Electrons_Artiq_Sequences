import numpy as np
from scipy.signal import find_peaks

def load_data(timestamp, ynames = ["ratio_signal"]):
    date, _ = timestamp.split("_")
    basefilename = f"/home/electrons/software/data/{date}/{timestamp}"
    xdata = np.genfromtxt(f"{basefilename}_arr_of_setpoints")
    ydata = {}
    for yname in ynames:
        ydata[yname] = np.genfromtxt(f"{basefilename}_{yname}")
    return xdata, ydata

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

def construct_scan_ranges(y, peaks):

    for i, pk in enumerate(peaks[0]):
        h_left = y[pk] - y[left_bases[i]]
        h_right = y[pk] - y[right_bases[i]]

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
        distance=5
    )
    peaks_lost = find_peaks(
        y_lost,
        height=max(6*noise_lost, 0.15),
        prominence=max(3*noise_lost, 0.10),
        distance=5
    )

    # Construct Fine Scan Ranges
    for pk in peaks_trapped