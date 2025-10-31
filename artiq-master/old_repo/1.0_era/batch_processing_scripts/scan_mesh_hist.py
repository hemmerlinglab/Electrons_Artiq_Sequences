import os

import subprocess
import numpy as np

min_volt = 0
max_volt = 200
steps = 11

no_of_repeats = 1e5


if __name__ == "__main__":

    volt_arr = np.linspace(min_volt, max_volt, steps)
    scans = []
    
    for v in volt_arr:
    
        print('Mesh voltage ' + str(v))
        cmd = 'artiq_run -q ../Electrons/Long_term_hist.py no_of_repeats=' + str(no_of_repeats) + ' mesh_voltage=' + str(v)
    
        output = subprocess.getoutput(cmd)
    
        out = output.split("\n")
    
        basefilename = out[2].split(' ')[1]
        scan_no = out[2].split('/')[6][0:15]
    
        scans.append([str(v), scan_no])
    
    
    f = open(basefilename + '_param_scan','w')
    
    f.write('# Scan no, mesh voltage \n')
    
    for k in range(len(scans)):
    
        hlp = str(scans[k][1]) + ', ' + str(scans[k][0]) + '\n'
        f.write(hlp)
    
    f.close()
    
    print("Scan list saved in ... " + basefilename)
    
    print('Setting Mesh Voltages back to 0V ...')
    
    os.system('artiq_run -q ../Testing_codes/mesh_voltage_calibration.py mesh_voltage=0')
