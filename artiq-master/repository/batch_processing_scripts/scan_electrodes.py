import os

import subprocess
import numpy as np
import time

time_count = 1
mesh_voltage = 150
min_volt = -10
max_volt = 9.9
steps = 40
repeat = 2

elec_dict = {
             'tl1': 0, 'tl2': 1, 'tl3': 2, 'tl4': 3, 'tl5': 4,
             'tr1': 9, 'tr2': 8, 'tr3': 7, 'tr4': 6, 'tr5': 5,
             'bl1': 12, 'bl2': 13, 'bl3': 14, 'bl4': 15, 'bl5': 16,
             'br1': 21, 'br2': 20, 'br3': 19, 'br4': 18, 'br5': 17
             }

if __name__ == '__main__':

    scans = []

    for e in elec_dict.keys():

        print('Scanning electrode ' + e)
        start_time = time.time()
        scan_no = []

        for i in range(repeat):
            cmd = 'artiq_run -q ../Electrons/Scan_DC_electrodes.py time_count=' + str(time_count) + ' mesh_voltage=' + str(mesh_voltage) + ' Zotino_channel=' + str(elec_dict[e]) + ' minimum=' + str(min_volt) + ' maximum=' + str(max_volt) + ' steps=' + str(steps)

            output = subprocess.getoutput(cmd)

            out = output.split('\n')
        
            basefilename = out[3].split(' ')[1]
            scan_no.append(out[3].split('/')[6][9:15])

        scans.append([e, scan_no])

        end_time = time.time()
        print('Time elapsed: ' + str(end_time-start_time) + 's.')

    f = open(basefilename + '_params_scan', 'w')

    f.write('Repeat = ' + str(repeat) + '\n')
    f.write('# Electrode, scan_numbers\n')

    for k in range(len(scans)):
        hlp = str(scans[k][0]) + ', ' + str(scans[k][1]) + '\n'
        f.write(hlp)
    
    f.close()

    print("Scan list saved in ... " + basefilename)
