import os

import subprocess
import numpy as np

#volts = [10, 20]
volts = [0, 10, 20, 30, 40, 50,
        60, 70, 80, 90, 100,
        110, 120, 130, 140, 150,
        160, 170, 180, 190, 200]
freq_422 = [709.078730, 709.078625, 709.078674, 709.078624, 709.078571, 709.078640,
            709.078623, 709.078625, 709.078621, 709.078623, 709.078640,
            709.078575, 709.078623, 709.078675, 709.078621, 709.078690,
            709., 709., 709., 709., 709.078710]
freq_390 = [766.817850, 766.817913, 766.817696, 766.817698, 766.817694, 766.817820,
            766.817800, 766.817902, 766.817903, 766.817903, 766.816600,
            766,817799, 766.817904, 766.817900, 766.817902, 766.817960,
            766., 766., 766., 766., 766.817850]
volt_arr = np.array(volts)

steps = 40
relock_steps = 4
lock_wait_time = 3000
relock_wait_time = 6000
no_of_repeats = 800
detection_time = 10000

range_radius_422 = 150
range_radius_390 = 250

if __name__ == "__main__":
    
    scans = []
    
    for i, v in enumerate(volt_arr):
    
        print('\nMesh voltage ' + str(v) + '\n')
        print('Scanning 422, center frequency = ' + str(freq_422[i]) + ', 390 frequency = ' + str(freq_390[i]) + '\n')
        cmd = 'artiq_run -q ../Electrons/scan_laser_frequency.py frequency_422=' + str(freq_422[i]) + ' frequency_390=' + str(freq_390[i]) + ' scanning_laser=422 min_freq=' + str(-range_radius_422) + ' max_freq=' + str(range_radius_422) + ' steps=' + str(steps) + ' relock_steps=' + str(relock_steps) + ' lock_wait_time=' + str(lock_wait_time) + ' relock_wait_time=' + str(relock_wait_time) + ' mesh_voltage=' + str(v) + ' no_of_repeats=' + str(no_of_repeats) + ' detection_time=' + str(detection_time)
    
        output = subprocess.getoutput(cmd)
        out = output.split('\n')
        for o in out:
            if o[0:6] == 'Scan /':
                basefilename = o.split(' ')[1]
                scan_no_422 = o.split('/')[6][0:15]
    
        counts = np.genfromtxt(basefilename + '_scan_result', delimiter = ',')
        freqs = np.genfromtxt(basefilename + '_act_freqs')
        maxfreq_422 = freqs[np.argmax(counts)]
        print('maxfreq_422 = ' + str(maxfreq_422))
    
        print('\nScanning 390, center frequency = ' + str(freq_390[i]) + ', 422 frequency = ' + str(maxfreq_422) + '\n')
        cmd = 'artiq_run -q ../Electrons/scan_laser_frequency.py frequency_422=' + str(maxfreq_422) + ' frequency_390=' + str(freq_390[i]) + ' scanning_laser=390 min_freq=' + str(-range_radius_390) + ' max_freq=' + str(range_radius_390) + ' steps=' + str(steps) + ' relock_steps=' + str(relock_steps) + ' lock_wait_time=' + str(lock_wait_time) + ' relock_wait_time=' + str(relock_wait_time) + ' mesh_voltage=' + str(v) + ' no_of_repeats=' + str(no_of_repeats) + ' detection_time=' + str(detection_time)
    
        output = subprocess.getoutput(cmd)
        out = output.split('\n')
        for o in out:
            if o[0:6] == 'Scan /':
                basefilename = o.split(' ')[1]
                scan_no_390 = o.split('/')[6][0:15]
    
        counts = np.genfromtxt(basefilename + '_scan_result', delimiter = ',')
        freqs = np.genfromtxt(basefilename + '_act_freqs')
        maxfreq_390 = freqs[np.argmax(counts)]
        print('maxfreq_390 = ' + str(maxfreq_390))
    
        scans.append([str(v), scan_no_422, scan_no_390, maxfreq_422, maxfreq_390])
    
    f = open(basefilename + '_param_scan', 'w')
    
    f.write('# Mesh voltage, Scan no (422), Max freq (422), Scan no (390), Max freq (390)\n')
    for k in range(len(scans)):
        hlp = str(scans[k][0]) + ', ' + str(scans[k][1]) + ', ' + str(scans[k][3]) + ', ' + str(scans[k][2]) + ', ' + str(scans[k][4]) + '\n'
        f.write(hlp)
    
    f.close()
    
    print('\nScan list and max frequencies saved in ... ' + basefilename)
    
    print('Setting Mesh Voltage back to 0V ...')
    
    os.system('artiq_run -q ../Testing_codes/mesh_voltage_calibration.py mesh_voltage=0')
