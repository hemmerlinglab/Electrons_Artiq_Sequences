import time
from typing import Tuple
from artiq_controller import SingleParameterScan
from helper_functions import find_best_laser_frequency


def run_with_422_relock(scanner, config, initialize=False, **run_kwargs):

    while True:

        if initialize:
            print("[Manager] Searching for laser 422 frequency ...")
            new_422_freq, _, _ = relock_laser(scanner, laser_to_relock=422)
            config["frequency_422"] = new_422_freq
            print("[Manager] Initialization Done, resuming to experiment scan ...")

        initialize = False
        t0 = time.time()

        ts = scanner.run(**run_kwargs)
        stdout, stderr = scanner.last_output

        if "LASER_OFF_422" in stderr:
            print("[Manager] Detected LASER_OFF_422 -> relock laser and retry scan.")

            new_422_freq, _, _ = relock_laser(scanner, laser_to_relock=422)
            config["frequency_422"] = new_422_freq

            print("[Manager] Resuming the interrupted scan ...")
            continue

        print(f"[Manager] Scan done in {time.time()-t0:.1f}s")
        return ts


def relock_laser(
    scanner:            SingleParameterScan,
    laser_to_relock:    int =   422,
    rough_scan_center:  float = 709.078,
    rough_scan_width:   float = 3e-3,
    rough_steps:        int =   61,
    rough_repeats:      int =   3000,
    fine_scan_width:    float = 2e-4,
    fine_steps:         int =   41,
    fine_repeats:       int =   10000,
) -> Tuple[float, str, str]:

    f0 = scanner.get_param(f"frequency_{laser_to_relock}")
    scanner.save_profile("experiment")

    scanner.set_param("no_of_repeats", rough_repeats)
    scanner.set_param("histogram_refresh", rough_repeats)

    print(f"[Relock_Laser] Scanning frequency_{laser_to_relock} [rough] ...")
    ts_rough = scanner.run(
        scanning_parameter = f"frequency_{laser_to_relock}",
        min_scan = rough_scan_center - rough_scan_width,
        max_scan = rough_scan_center + rough_scan_width,
        steps = rough_steps,
    )
    freq_rough = find_best_laser_frequency(ts_rough)
    print(f"[Relock_Laser] Scan Result: {freq_rough:6f} THz")

    scanner.set_param("no_of_repeats", fine_repeats)
    scanner.set_param("histogram_refresh", fine_repeats)

    print(f"[Relock_Laser] Scanning frequency_{laser_to_relock} [fine] ...")
    ts_fine = scanner.run(
        scanning_parameter = f"frequency_{laser_to_relock}",
        min_scan = freq_rough - fine_scan_width,
        max_scan = freq_rough + fine_scan_width,
        steps = fine_steps
    )
    freq_fine = find_best_laser_frequency(ts_fine)
    print(f"[Relock_Laser] Scan Result: {freq_fine:6f} THz")

    # Recover experiment configs but with the new laser frequency
    scanner.load_profile("experiment")
    scanner.delete_profile("experiment")
    scanner.set_param(f"frequency_{laser_to_relock}", freq_fine)

    if f0 is None:
        print(f"frequency_{laser_to_relock} set to {freq_fine:.6f} THz")
    else:
        print(f"frequency_{laser_to_relock} updated: {f0:.6f} -> {freq_fine:.6f} THz")

    return freq_fine, ts_rough, ts_fine