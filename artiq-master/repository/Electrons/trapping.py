from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

from dc_electrodes import *

class Trapping(EnvExperiment):
    
    def build(self):
        
        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl16') # For sending triggering signal of the AWG
        self.setattr_device('scheduler')
        self.setattr_device('zotino0')

        # Setting the lock frequency for 422 and the scan range for 390
        self.my_setattr('frequency_422', NumberValue(default=709.077801,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('min_freq', NumberValue(default=-1000,unit='MHz',scale=1,ndecimals=6,step=1))
        self.my_setattr('max_freq', NumberValue(default=1000,unit='MHz',scale=1,ndecimals=6,step=1))
        self.my_setattr('steps', NumberValue(default=10,unit='steps to scan',scale=1,ndecimals=0,step=1))

        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=150,unit='V',scale=1,ndecimals=0,step=1))

        # Setmy_ting pafor the experiment
        self.my_setattr('no_of_averages', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('no_of_repeats', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('detection_time', NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))

        self.electrodes = Electrodes()

        return

    def my_setattr(self, arg, val):
        
        # define the attribute
        self.setattr_argument(arg,val)

        # add each attribute to the config dictionary
        if hasattr(val, 'unit'):
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'unit' : '" + str(val.unit) + "'})")
        else:
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + "})")



    @kernel
    def set_mesh_voltage(self, voltage):
        
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(0, 65000)
        self.zotino0.write_dac(0, 1.0/200.0 * voltage)
        self.zotino0.load()



    @kernel
    def set_electrode_voltages(self, channel_list, voltage_list):
        
        voltage = 0

        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)

        for k in range(len(channel_list)):
        #for k in [0,1]:

            self.zotino0.write_gain_mu(channel_list[k], 65000)
            self.zotino0.load()
            delay(200*us)
            self.zotino0.write_dac(channel_list[k], voltage_list[k])
            self.zotino0.load()
            delay(200*us)

        return



    def prepare(self):
        
        # Calculate the frequencies for scanning
        self.scan_values = self.frequency_422 + 1e-6 * np.linspace(self.min_freq, self.max_freq, self.steps)
        # Set the path of the setpoint files
        self.filepath_422 = '/home/electrons/server/422_setpoint.txt'
        self.filepath_390 = '/home/electrons/server/390_setpoint.txt'
        
        # Create the dataset of the result
        self.set_dataset('set_points', [0] * len(self.scan_values), broadcast=True)
        self.set_dataset('act_freqs', [0] * len(self.scan_values), broadcast=True)
        self.set_dataset('scan_result', [0.0] * len(self.scan_values), broadcast=True)
        
        # Set the data going to save
        self.data_to_save = [{'var' : 'set_points', 'name' : 'set_points'},
                             {'var' : 'act_freqs', 'name' : 'act_freqs'},
                             {'var' : 'scan_result', 'name' : 'counts'}]

        # save sequence file name
        self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})

        get_basefilename(self)

        self.core.reset() # Reset the core

    def analyze(self):
        
        print('saving data...')
        save_all_data(self)

        # overwrite config file with complete configuration
        self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
        save_config(self.basefilename, self.config_dict)

        add_scan_to_list(self)
        
        print('Scan ' + self.basefilename + ' finished.')
        print('Scan finished.')

    def set_single_laser(self, frequency):
        
        # Write the frequency value to the file
        # Notice that the default output path of ARTIQ is /artiq-master/results/(date and time)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('192.168.42.136', 63700)

        print('sending new setpoint: ' + str(frequency))
        sock.connect(server_address)
        
        my_str = "{0:.9f}".format(frequency)

        #print(my_str)
        #print(my_str.encode())
        try:
            sock.sendall(my_str.encode())

        finally:

            sock.close()        
        
        return


    @kernel
    def counting(self):
        
        # Preparations
        self.core.break_realtime()
        data = [0] * self.no_of_averages
        trigger_length = 50.0 * ns
        
        # Works
        for j in range(self.no_of_averages):
            with parallel:
                # Send signals for triggering
                with sequential:
                    
                    delay(trigger_length)
                    
                    self.ttl16.pulse(trigger_length)
                    delay(1.0 * self.detection_time * us)
                    delay(1 * us)
                
                # Count the rising edge in a small time window after the triggering pulse was sent
                with sequential:
                    delay(trigger_length)
                    ev = self.ttl3.gate_rising(self.detection_time * us)
                    data[j] = self.ttl3.count(ev)
                    delay(1.0 * self.detection_time * us)
                    delay(1 * us)

                    delay(trigger_length)
        
        # Store the result
        self.set_dataset('single_freq_count', (data), broadcast = True)

    def run(self):
        
        # Set voltage of the mesh
        #self.set_mesh_voltage(self.mesh_voltage)
       
        self.multipole_vector = {
                'Ex' : 0,
                'Ey' : 0,
                'Ez' : 0,
                'U1' : 0,
                'U2' : -0.65,
                'U3' : 0,
                'U4' : 0,
                'U5' : 0
            }


        (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
        print(chans)
        print(voltages)

        

        chans = list(range(20))
        voltages = list(range(-10, 10, 1))

        print(chans)
        print(voltages)
        print(len(voltages))

        self.set_electrode_voltages(chans, voltages)

        return

        # Lock the frequency of 422

        # Scan frequencies of 390 and store the result
        self.scan_results = [0.0] * len(self.scan_values)
        
        for i in range(len(self.scan_values)):

            print("{0}/{1}: {2:.6f}".format(i, len(self.scan_values), self.scan_values[i]))
            
            self.set_single_laser(self.scan_values[i])
            if i == 0:
                time.sleep(3)
            else:
                time.sleep(1)
            
            # to get more averages repeat the 500 averages and average again
            avg_counts = 0
            for k in range(self.no_of_repeats):
                self.counting()
                cts = np.array(self.get_dataset('single_freq_count'))
                avg_counts += np.mean(cts)
            avg_counts /= self.no_of_repeats

            self.scan_results[i] = avg_counts
 
            # read laser frequencies
            self.wavemeter_frequencies = get_laser_frequencies()
            #self.wavemeter_frequencies = 0
            

            self.mutate_dataset('scan_result', i, avg_counts)        
            self.mutate_dataset('act_freqs', i, self.wavemeter_frequencies)
            self.mutate_dataset('set_points', i, self.scan_values[i])
        
        #print('array:', self.scan_results)



