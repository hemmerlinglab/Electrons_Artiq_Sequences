import os

import subprocess
import numpy as np

#volts = [10, 20]
volts = [190]
volt_arr = np.array(volts)

frequency_422 = 709.078700
frequency_390 = 766.817850
steps = 40
relock_steps = 4
lock_wait_time = 3000
relock_wait_time = 6000
no_of_repeats = 800
detection_time = 10000

range_radius_422 = 1000
range_radius_390 = 2000

scans = []

if __name__ == "__main__":
    for v in volt_arr:
    
        print("\nMesh voltage " + str(v) + "\n")
        print("Scanning 422, center frequency = " + str(frequency_422) + ", 390 frequency = " + str(frequency_390) + "\n")
        cmd = "artiq_run -q ../Electrons/scan_laser_frequency.py frequency_422=" + str(frequency_422) + " frequency_390=" + str(frequency_390) + " scanning_laser='422' min_freq=" + str(-range_radius_422) + " max_freq=" + str(range_radius_422) + " steps=" + str(steps) + " relock_steps=" + str(relock_steps) + " lock_wait_time=" + str(lock_wait_time) + " relock_wait_time=" + str(relock_wait_time) + " mesh_voltage=" + str(v) + " no_of_repeats=" + str(no_of_repeats) + " detection_time=" + str(detection_time)

        output = subprocess.getoutput(cmd)
        out = output.split("\n")
        for o in out:
            if o[0:6] == "Scan /":
                basefilename = o.split(" ")[1]
                scan_no_422 = o.split("/")[6][0:15]
    
        counts = np.genfromtxt(basefilename + "_scan_result", delimiter = ",")
        freqs = np.genfromtxt(basefilename + "_act_freqs")
        maxfreq_422 = freqs[np.argmax(counts)]
        print("maxfreq_422 = " + str(maxfreq_422))
    
        print("\nScanning 390, center frequency = " + str(frequency_390) + ", 422 frequency = " + str(maxfreq_422) + "\n")
        cmd = "artiq_run -q ../Electrons/scan_laser_frequency.py frequency_422=" + str(maxfreq_422) + " frequency_390=" + str(frequency_390) + " scanning_laser='390' min_freq=" + str(-range_radius_390) + " max_freq=" + str(range_radius_390) + " steps=" + str(steps) + " relock_steps=" + str(relock_steps) + " lock_wait_time=" + str(lock_wait_time) + " relock_wait_time=" + str(relock_wait_time) + " mesh_voltage=" + str(v) + " no_of_repeats=" + str(no_of_repeats) + " detection_time=" + str(detection_time)
    
        output = subprocess.getoutput(cmd)
        out = output.split("\n")
        for o in out:
            if o[0:6] == "Scan /":
                basefilename = o.split(" ")[1]
                scan_no_390 = o.split("/")[6][0:15]
    
        counts = np.genfromtxt(basefilename + "_scan_result", delimiter = ",")
        freqs = np.genfromtxt(basefilename + "_act_freqs")
        maxfreq_390 = freqs[np.argmax(counts)]
        print("maxfreq_390 = " + str(maxfreq_390))
    
        scans.append([str(v), scan_no_422, scan_no_390, maxfreq_422, maxfreq_390])
    
    f = open(basefilename + "_param_scan", "w")
    
    f.write("# Mesh voltage, Scan no (422), Max freq (422), Scan no (390), Max freq (390)\n")
    for k in range(len(scans)):
        hlp = str(scans[k][0]) + ", " + str(scans[k][1]) + ", " + str(scans[k][3]) + ", " + str(scans[k][2]) + ", " + str(scans[k][4]) + "\n"
        f.write(hlp)
    
    f.close()
    
    print("\nScan list and max frequencies saved in ... " + basefilename)
    
    print("Setting Mesh Voltage back to 0V ...")
    
    os.system("artiq_run -q ../Testing_codes/mesh_voltage_calibration.py mesh_voltage=0")
