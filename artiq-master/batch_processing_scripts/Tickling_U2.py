from artiq_controller import ArtiqController
from helper_functions import calculate_fine_scan_range, find_optima
import numpy as np

# 1. Global Settings ------------------------------------------------
# script to run
script_path = "/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/Modular/general_scan.py"
save_path = "/home/electrons/software/data/"
# persistent configs
general_config = {
    "mode": "Trapping",
    "mesh_voltage": 120,
    "MCP_front": 450,
    "wait_time": 90,
    "load_time": 210,
    "trap": "Single PCB",
    "frequency_422": 709.07830,
    "frequency_390": 768.74785,
    "RF_on": True,
    "RF_frequency": 1.732,
    "ext_pulse_length": 900,
    "ext_pulse_amplitude": 15,
    "U1": 0,
    "U3": 0,
    "U4": 0,
    "U5": 0
}
# initial only configs
initial_config = {
    "Ex": -0.13,
    "Ey": 0.11,
    "Ez": 0.03
}

# 2. Scan Settings --------------------------------------------------
U2_to_scan = np.linspace(-0.05, -0.25, 21)
RF_amplitude_to_scan = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0])
default_U2 = -0.13
default_RF_amplitude = 4.0
rough_scans = {
    "Ex": {"min": -1.0, "max": 1.0, "steps": 21},
    "Ey": {"min": -0.2, "max": 0.2, "steps": 41}, # single scan pass
    "Ez": {"min": -0.8, "max": 0.8, "steps": 17}
}
no_of_repeats = {
    "compensation": 2000,
    "spectrum": 10000
}
scan_Ex_config = {
    "tickle_on": False,
    "scanning_parameter": "Ex",
    "min_scan": -1.0,
    "max_scan": 1.0,
    "steps": 21
}
scan_Ey_config = {
    "tickle_on": False,
    "scanning_parameter": "Ey",
    "min_scan": -0.2,
    "max_scan": 0.2,
    "steps": 41
}
scan_Ez_config = {
    "tickle_on": False,
    "scanning_parameter": "Ez",
    "min_scan": -0.8,
    "max_scan": 0.8,
    "steps": 17
}
scan_spectrum_config = {
    "tickle_on": True,
    "tickle_level": -10,
    "tickle_pulse_length": 80,
    "scanning_parameter": "tickle_frequency",
    "min_scan": 1,
    "max_scan": 150,
    "steps": 150
}

# 3. Initialization -------------------------------------------------
ac = ArtiqController(script_path)
ac.load_params(initial_config)
experiment_list = {}

# 4. Perform Experiments --------------------------------------------
for i, u2 in enumerate(U2_to_scan):
    print(f"========== Step {i+1}/{len(U2_to_scan)}: U2 = {u2:.2f} ==========")
    u2 = float(f"{u2:.2f}")
    ac.set_param("U2", u2)
    ac.set_param("RF_amplitude", default_RF_amplitude)
    key = f"exp{i}"
    experiment_list[key] = {"U2": u2}

    print("Scanning Ex (Rough) ...")
    ac.load_params(general_config)
    ac.load_params(scan_Ex_config)
    ac.print_args() # Test
    #timestamp = ac.run()
    #experiment_list[key]["Ex_rough"] = {"timestamp": timestamp, "params": ac.get_params()}
    #min_scan, max_scan, steps = calculate_fine_scan_range(timestamp, stepsize = 0.01)
    from helper_functions import dummy_fine_scan_range, dummy_optima
    min_scan, max_scan, steps = dummy_fine_scan_range()

    print(f"Scanning Ex (Fine), range = [{min_scan:.2f}, {max_scan:.2f}] ...")
    ac.set_param("min_scan", min_scan)
    ac.set_param("max_scan", max_scan)
    ac.set_param("steps", steps)
    ac.print_args()
    #timestamp = ac.run()
    #Ex_new = find_optima(timestamp)
    #experiment_list[key]["Ex_fine"] = {"timestamp": timestamp, "params": ac.get_params()}
    Ex_new = dummy_optima()
    ac.set_param("Ex", Ex_new)

    print("Scanning Ey ...")
    ac.load_params(scan_Ey_config)
    ac.print_args()
    #timestamp = ac.run()
    #Ey_new = find_optima(timestamp)
    #experiment_list[key]["Ey"] = {"timestamp": timestamp, "params": ac.get_params()}
    Ey_new = dummy_optima()
    ac.set_param("Ey", Ey_new)

    print("Scanning Ez (Rough) ...")
    ac.load_params(scan_Ez_config)
    ac.print_args()
    #timestamp = ac.run()
    #min_scan, max_scan, steps = calculate_fine_scan_range(timestamp, stepsize = 0.01)
    #experiment_list[key]["Ez_rough"] = {"timestamp": timestamp, "params": ac.get_params()}
    min_scan, max_scan, steps = dummy_fine_scan_range()

    print(f"Scanning Ez (Fine), range = [{min_scan:.2f}, {max_scan:.2f}] ...")
    ac.set_param("min_scan", min_scan)
    ac.set_param("max_scan", max_scan)
    ac.set_param("steps", steps)
    ac.print_args()
    #timestamp = ac.run()
    #Ex_new = find_optima(timestamp)
    #experiment_list[key]["Ez_fine"] = {"timestamp": timestamp, "params": ac.get_params()}
    Ez_new = dummy_optima()
    ac.set_param("Ez", Ez_new)

    print("Field compensation done, scanning spectrum ...")
    ac.load_params(scan_spectrum_config)
    ac.print_args()
    #timestamp = ac.run()
    #experiment_list[key]["spectrum"] = {"timestamp": timestamp, "params": ac.get_params()}

# save `experiment_list`
#date, time = timestamp.split("_")
#file = f"{save_path}/{date}/{date}_{time}_batch_scans"