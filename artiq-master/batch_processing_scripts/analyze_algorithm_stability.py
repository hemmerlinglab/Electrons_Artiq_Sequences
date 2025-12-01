import numpy as np
from artiq_controller import FindOptimalE

# 1) Settings -------------------------------------------------------
general_config = {
    "histogram_on": True,
    "bin_width": 1.0,
    "histogram_refresh": 1000,
    "mesh_voltage": 120,
    "MCP_front": 400,
    "threshold_voltage": 60,
    "wait_time": 90,
    "load_time": 210,
    "trap": "Single PCB",
    "flip_electrodes": False,
    "frequency_422": 709.078300,
    "frequency_390": 768.708843,
    "RF_on": True,
    "RF_frequency": 1.732,
    "ext_pulse_length": 900,
    "ext_pulse_level": 15.0,
    "U1": 0, "U3": 0, "U4": 0, "U5": 0,
}
optimizer_config = {
    "optimize_target": "ratio_signal",
    "max_iteration": 50,
    "min_iteration": 5,
    "init_sample_size": 10,
    "tolerance": 1e-3,
    "converge_count": 3,
    "n_candidate_run": 1024,
    "n_candidate_anal": 4096,
    "min_Ex": -0.4, "max_Ex": 0.2,
    "min_Ey": -0.1, "max_Ey": 0.2,
    "min_Ez": -0.1, "max_Ez": 0.1,
    "no_of_repeats": 3000,
}

# 2) Run ------------------------------------------------------------
def run_many_optimizations(n_runs: int = 10):
    """
    Repeatedly run find_optimal_E.py and analyze stability of the two optimal E's.

    Returns:
        obs_arr, model_arr  (both shape: [n_runs, 3])
    """
    observed_Es = []
    model_Es = []

    for i in range(n_runs):
        print(f"\n========== Optimization run {i+1}/{n_runs} ==========")

        opt = FindOptimalE()

        # Merge optimizer_config and general_config into kwargs
        # optimizer_config keys match explicit args of FindOptimalE.run
        # general_config keys go via **extra_params
        run_kwargs = {}
        run_kwargs.update(optimizer_config)
        run_kwargs.update(general_config)

        E_best_obs, E_best_model = opt.run(**run_kwargs)

        print(f"Best observed E (Ex, Ey, Ez): {E_best_obs}")
        print(f"Best model    E (Ex, Ey, Ez): {E_best_model}")

        observed_Es.append(E_best_obs)
        model_Es.append(E_best_model)

    # Convert to arrays for statistics
    obs_arr = np.array(observed_Es, dtype=float)   # shape (n_runs, 3)
    model_arr = np.array(model_Es, dtype=float)    # shape (n_runs, 3)

    # Helper to summarize a set of vectors
    def summarize(label: str, arr: np.ndarray):
        mean = arr.mean(axis=0)
        std = arr.std(axis=0, ddof=1) if arr.shape[0] > 1 else np.zeros(3)
        median = arr.median(axis=0)
        print(f"\n{label}:")
        print(f"  mean   Ex, Ey, Ez = {mean}")
        print(f"  std    Ex, Ey, Ez = {std}")
        print(f"  median Ex, Ey, Ez = {median}")

    summarize("Best observed E", obs_arr)
    summarize("Best model E", model_arr)

    # Difference between observed and model optimum per run
    delta = obs_arr - model_arr
    summarize("Observed E - Model E", delta)

    # Also print RMS magnitude of fluctuations if you care
    obs_fluct = obs_arr - obs_arr.mean(axis=0, keepdims=True)
    model_fluct = model_arr - model_arr.mean(axis=0, keepdims=True)
    obs_rms = np.sqrt((obs_fluct ** 2).sum(axis=1)).mean()
    model_rms = np.sqrt((model_fluct ** 2).sum(axis=1)).mean()

    print(f"\nRMS fluctuation magnitude over runs:")
    print(f"  observed E: {obs_rms}")
    print(f"  model    E: {model_rms}")

    return obs_arr, model_arr


if __name__ == "__main__":
    # change n_runs if you want more/less statistics
    run_many_optimizations(n_runs=10)
