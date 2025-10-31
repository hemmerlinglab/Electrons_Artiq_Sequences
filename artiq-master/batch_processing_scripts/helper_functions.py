import numpy as np

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
