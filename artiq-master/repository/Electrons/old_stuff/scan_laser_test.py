'''Zijue Luo: trying to write a code to scan the Moglab laser and lock the Toptica laser'''

from artiq.experiment import *
import numpy as np

import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *



class Scan_Laser(EnvExperiment):
    
    def build(self):
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl16') # For sending triggering signal of the AWG
        self.setattr_device('scheduler')

        # Setting the lock frequency for 422 and the scan range for 390
        self.setattr_argument('frequency_422', NumberValue(default=709.077801,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.setattr_argument('min_390', NumberValue(default=766.756652,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.setattr_argument('max_390', NumberValue(default=768.838333,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.setattr_argument('steps', NumberValue(default=100,unit='steps to scan',scale=1,ndecimals=0,step=1))

        # Setting parameters for the experiment
        self.setattr_argument('no_of_averages', NumberValue(default=500,unit='detections for one data',scale=1,ndecimals=0,step=1))
        self.setattr_argument('detection_time', NumberValue(default=1,unit='us',scale=1,ndecimals=0,step=1))

    def prepare(self):
        
        # Calculate the frequencies for scanning
        self.scan_values = np.linspace(self.min_390, self.max_390, self.steps)
        # Set the path of the setpoint files
        self.filepath_422 = '/home/electrons/server/422_setpoint.txt'
        self.filepath_390 = '/home/electrons/server/390_setpoint.txt'
        
        # Create the dataset of the result
        self.set_dataset('set_points_390', self.scan_values, broadcast=True)
        self.set_dataset('scan_result', [0.0] * len(self.scan_values), broadcast=True)
        
        # Set the data going to save
        self.data_to_save = [{'var' : 'set_points_390', 'name' : 'set+points'},
                             {'var' : 'scan_result', 'name' : 'counts'}]
        get_basefilename(self)

        self.core.reset() # Reset the core

    def analyze(self):
        
        print('saving data...')
        save_all_data(self)
        print('Data saved!')

    def set_single_laser(self, filepath, frequency):
        
        # Write the frequency value to the file
        # Notice that the default output path of ARTIQ is /artiq-master/results/(date and time)
        setpoint_file = open(filepath, 'w')
        setpoint_file.write("{0:.6f}".format(frequency))
        setpoint_file.close()

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
        
        # Lock the frequency of 422
        self.set_single_laser(self.filepath_422, self.frequency_422)

        time.sleep(2)

        # Scan frequencies of 390 and store the result
        self.scan_results = [0.0] * len(self.scan_values)
        for i in range(len(self.scan_values)):

            print(self.scan_values[i])
            time.sleep(1)

            self.scheduler.pause()
            self.set_single_laser(self.filepath_422, self.scan_values[i])
            self.counting()
            cts = np.array(self.get_dataset('single_freq_count'))
            avg_counts = np.mean(cts)
            self.mutate_dataset('scan_result', i, avg_counts)
            self.scan_results[i] = avg_counts
        
        #print('array:', self.scan_results)



