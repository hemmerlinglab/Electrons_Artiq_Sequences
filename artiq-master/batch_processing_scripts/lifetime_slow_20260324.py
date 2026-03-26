import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/artiq_controller")
from artiq_controller import SingleParameterScan
from experiment_functions import run_with_422_relock


# 1) Global Settings
# ===================================================================
config = {
    "mode": "Lifetime",
    "histogram_on": True,
    "bin_width": 1.0,
    "histogram_refresh": 1000,
    "mesh_voltage": 130,
    "MCP_front": 500,
    "threshold_voltage": 60,
    "load_time": 260,
    "wait_times_path": "/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions/Table/",
    "repeats_ratio": 1,
    "frequency_390": 768.708843,
    "laser_failure": "raise error",
    "RF_on": True,
    "RF_amp_mode": "setpoint",
    "RF_frequency": 1.732,
    "RF_amplitude": 2.5,
    "ext_pulse_length": 900,
    "ext_pulse_level": 15.0,
    "U1": 0, "U2": -0.25, "U3": 0, "U4": 0, "U5": 0,
    "Ex": -0.119, "Ey": 0.07, "Ez": 0.056, 
    "tickle_on": False,
    "tickle_level": -10.0,
    "tickle_pulse_length": 130,
}

# 2) Scan settings
# =================================================================
tables = [ 
    "lifetime_wait_times_slow_20260324 (2).csv", 
    "lifetime_wait_times_slow_20260324 (3).csv", 
    "lifetime_wait_times_slow_20260324 (4).csv", 
    "lifetime_wait_times_slow_20260324 (5).csv", 
    "lifetime_wait_times_slow_20260324 (6).csv"
]


# 3) Run Experiments
# ===================================================================
scanner = (
    SingleParameterScan()
    .load_params(config)
)
timestamp = []

initialize = True

for i, table in enumerate(tables):    

    print(f"running experiment {i}/{len(tables)} with file {table} ...")
    scanner.set_param("wait_times_file", table)

    ts = run_with_422_relock(
        scanner, config,
        initialize=initialize,
        scanning_parameter="tickle_frequency",
        min_scan = 1,
        max_scan = 100,
        steps = 100,
    )
    initialize = False
    timestamp.append(ts)

    print(f"scan complete, experiment timestamp: {ts}")

print(timestamp)

