import numpy as np
from scipy.optimize import curve_fit
from tqdm.auto import tqdm

# Multiprocessing in Fitting
# ===============================================
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

# --- multiprocessing worker context (top-level) ---
_FIT_CTX = {}

def _init_fit_worker(x, y, n_peaks, mode, stepsize, init_mus, bounds, c0, sigma0, max_nfev):
    """
    Runs once per worker process. Stores arrays + config in a global dict
    so each task only needs to send the mu0_tuple (plus idx).
    """
    global _FIT_CTX
    _FIT_CTX = {
        "x": np.asarray(x, dtype=float),
        "y": np.asarray(y, dtype=float),
        "n_peaks": int(n_peaks),
        "mode": mode,
        "stepsize": float(stepsize),
        "init_mus": list(init_mus),
        "bounds": bounds,
        "c0": float(c0),
        "sigma0": float(sigma0),
        "max_nfev": int(max_nfev),
    }

def _fit_worker(task):
    """
    task = (idx, mu0_tuple)
    returns (idx, entry_dict)
    """
    global _FIT_CTX
    idx, mu0_tuple = task

    x = _FIT_CTX["x"]
    y = _FIT_CTX["y"]
    n_peaks = _FIT_CTX["n_peaks"]
    mode = _FIT_CTX["mode"]
    init_mus = _FIT_CTX["init_mus"]
    bounds = _FIT_CTX["bounds"]
    c0 = _FIT_CTX["c0"]
    sigma0 = _FIT_CTX["sigma0"]
    max_nfev = _FIT_CTX["max_nfev"]

    mu0s = init_mus + list(mu0_tuple)

    # Build p0 EXACTLY as your serial code: [c0, amp1, mu1, sigma1, ...]
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
            "r2": float(r2),
            "aicc": float(aicc),
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
            "err": str(e),
        }

    return idx, entry

# Analyze Fine Scan Helpers
# ===============================================
def _extract_mus_from_popt(popt, n_peaks):
    # popt = [c0, amp1, mu1, sigma1, amp2, mu2, sigma2, ...]
    mus = []
    for i in range(n_peaks):
        mus.append(float(popt[1 + 3*i + 1]))
    return mus

def fit_n_peaks(x, y, n_peaks, mode, stepsize, init_mus,
                scan_count=50, max_nfev=20000, n_jobs=1):
    """
    Fit data with n_peaks gaussian peaks. Existing peaks are seeded by init_mus.
    If one new peak is added, scan scan_count possible mu0 for the new peak.

    Returns: (best_entry, history_list)
    best_entry is the entry with highest R2 (same as your original logic).
    """

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_min, x_max = np.min(x), np.max(x)

    c0 = baseline_guess(y, mode)
    sigma0 = sigma_guess(x, stepsize)

    # Candidate mu0 list (unchanged)
    if (n_peaks - len(init_mus)) == 1:
        mu0_to_scan = [(mu0,) for mu0 in np.linspace(x_min, x_max, scan_count)]
    elif (n_peaks - len(init_mus)) == 0:
        mu0_to_scan = [()]
    else:
        raise ValueError("Not Supported!")

    bounds = build_bounds(n_peaks, x_min, x_max, stepsize, mode)

    total = len(mu0_to_scan)
    history = [None] * total
    best = None

    desc = f"[Fitter] mode={mode} n_peaks={n_peaks}"

    # -----------------------
    # Serial path
    # -----------------------
    if n_jobs is None or n_jobs <= 1 or total <= 1:
        for idx, mu0_tuple in enumerate(tqdm(mu0_to_scan, total=total, desc=desc, leave=False)):
            mu0s = list(init_mus) + list(mu0_tuple)

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
                    "r2": float(r2),
                    "aicc": float(aicc),
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
                    "err": str(e),
                }

            history[idx] = entry
            if entry["ok"] and ((best is None) or (entry["r2"] > best["r2"])):
                best = entry

        return best, history

    # -----------------------
    # Multiprocessing path
    # -----------------------
    n_jobs_eff = int(max(1, min(int(n_jobs), total)))
    tasks = [(idx, mu0_tuple) for idx, mu0_tuple in enumerate(mu0_to_scan)]

    with ProcessPoolExecutor(
        max_workers=n_jobs_eff,
        initializer=_init_fit_worker,
        initargs=(x, y, n_peaks, mode, stepsize, init_mus, bounds, c0, sigma0, max_nfev),
    ) as ex:

        futures = [ex.submit(_fit_worker, t) for t in tasks]

        with tqdm(total=total, desc=desc, leave=False) as pbar:
            for fut in as_completed(futures):
                idx, entry = fut.result()
                history[idx] = entry

                if entry["ok"] and ((best is None) or (entry["r2"] > best["r2"])):
                    best = entry

                pbar.update(1)

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
