from artiq_controller import DoeScan, FindOptimalE
import numpy as np

# 1) Meta Settings
# ===================================================================
save_path = "/home/electrons/software/data/"

# 2) Global Settings
# ===================================================================
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
    "U1": 0, "U3": 0, "U4": 0, "U5": 0
}

optimizer_config = {
    "optimize_target": "ratio_weighted",
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
    "no_of_repeats": 3000
}

experiment_config = {
    "utility_mode": "DOE Scan",
    "tickle_on": True,
    "tickle_level": -10.0,
    "tickle_pulse_length": 80,
    "no_of_repeats": 40000
}

# 3) Scan Settings
# ===================================================================
doe_file = "rf_1-120_shuffled.csv"  # unused for now; you can wire it into experiment_config if needed
RF_amplitudes_to_scan = [0, 0.5, 1, 1.5, 2, 2.6, 3.3, 4, 5, 6, 8, 11]
default_U2 = -0.18

OPTIMIZE_REPEAT = 5
delta_Ex, delta_Ey, delta_Ez = 0.05, 0.05, 0.05

# 4) Perform Experiments
# ===================================================================
experiment_list = {}

# Initial Optimization
opt = (
    FindOptimalE()
    .load_params(general_config)
    .set_param("min_Ex", -0.4)
    .set_param("max_Ex", 0.2)
    .set_param("min_Ey", -0.1)
    .set_param("max_Ey", 0.2)
    .set_param("min_Ez", -0.1)
    .set_param("max_Ez", -0.1)
)
E_center, _ = opt.run(
    optimize_target = "ratio_signal",
    max_iteration = 90
    tolerance = 1e-3,
    no_of_repeats = 5000
)

for i, rf_amp in enumerate(RF_amplitudes_to_scan):

    rf_amp = round(rf_amp, 2)
    min_Ex_local = round(E_center[0] - delta_Ex, 2)
    max_Ex_local = round(E_center[0] + delta_Ex, 2)
    min_Ey_local = round(E_center[1] - delta_Ey, 2)
    max_Ey_local = round(E_center[1] + delta_Ey, 2)
    min_Ez_local = round(E_center[2] - delta_Ez, 2)
    max_Ez_local = round(E_center[2] + delta_Ez, 2)

    print(f"========== Step {i+1}/{len(RF_amplitudes_to_scan)}: RF_amplitude = {rf_amp:.2f} ==========")

    # E field optimization
    opt = (
        FindOptimalE()
        .load_params(general_config)
        .set_param("min_Ex", min_Ex_local)
        .set_param("max_Ex", max_Ex_local)
        .set_param("min_Ey", min_Ey_local)
        .set_param("max_Ey", max_Ey_local)
        .set_param("min_Ez", min_Ez_local)
        .set_param("max_Ez", max_Ez_local)
    )
    E_fields = np.zeros((OPTIMIZE_REPEAT, 3))
    for i in range(OPTIMIZE_REPEAT):
        E_fields[i, :] = opt.run(
            optimize_target = "ratio_signal",
            max_iteration = 30,
            tolerance = 5e-3,
            no_of_repeats = 3000
        )


    # Parameters shared between optimizer and DOE scan for this RF amplitude
    shared_params = {
        "U2": default_U2,
        "RF_amplitude": rf_amp,
    }
    # Merge in any global config
    shared_params.update(general_config)

    # -------------------------------------------------
    # 4a) Find optimal E for this RF_amplitude
    # -------------------------------------------------
    print(f"Finding Optimal E for RF_amplitude = {rf_amp} ...")

    opt = FindOptimalE()
    opt.load_params(shared_params)
    opt.load_params(optimizer_config)

    # Optional: inspect the ARTIQ command line
    opt.print_args()

    # Actually run the optimizer and get both E's
    E_best_obs, E_best_model = opt.run()

    print("  -> Best observed E:", E_best_obs)
    print("  -> Best model E:   ", E_best_model)

    # Store results for later use if you want
    experiment_list[rf_amp] = {
        "E_best_obs": E_best_obs,
        "E_best_model": E_best_model,
    }

    # -------------------------------------------------
    # 4b) Perform DOE scan for this RF_amplitude
    # -------------------------------------------------
    print(f"Performing DOE spectrum scan for RF_amplitude = {rf_amp} ...")

    doe = DoeScan()
    doe.load_params(shared_params)
    doe.load_params(experiment_config)

    # If you want to use a specific DOE file name derived from rf_amp, do it here:
    # if doe_file:
    #     doe.set_param("doe_file_name", doe_file)

    # Optional: inspect ARTIQ command line for the DOE scan
    doe.print_args()

    # Run DOE scan (returns timestamp string if you care)
    ts = doe.run()
    print(f"  -> DOE scan timestamp: {ts}")
