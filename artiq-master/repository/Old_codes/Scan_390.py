from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *



class Scan_390(EnvExperiment):
    
    def build(self):
        
        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl16') # For sending triggering signal of the AWG
        self.setattr_device('scheduler')
        self.setattr_device('zotino0')

        # Setting the lock frequency for 422 and the scan range for 390
        self.my_setattr('frequency_422', NumberValue(default=709.078540,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('frequency_390', NumberValue(default=766.056,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('min_freq', NumberValue(default=-1000,unit='MHz',scale=1,ndecimals=6,step=1))
        self.my_setattr('max_freq', NumberValue(default=1000,unit='MHz',scale=1,ndecimals=6,step=1))
        self.my_setattr('steps', NumberValue(default=10,unit='steps to scan',scale=1,ndecimals=0,step=1))
        
        self.my_setattr('relock_422_steps', NumberValue(default=3,unit='',scale=1,ndecimals=0,step=1))
        
        self.my_setattr('relock_wait_time', NumberValue(default=1000,unit='ms',scale=1,ndecimals=1,step=1))
        self.my_setattr('lock_wait_time', NumberValue(default=1000,unit='ms',scale=1,ndecimals=1,step=1))

        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=150,unit='V',scale=1,ndecimals=0,step=1))

        # Setmy_ting pafor the experiment
        self.my_setattr('no_of_averages', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('no_of_repeats', NumberValue(default=1,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('detection_time', NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))



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

    def prepare(self):
        
        # Calculate the frequencies for scanning
        self.scan_values = self.frequency_390 + 1e-6 * np.linspace(self.min_freq, self.max_freq, self.steps)
        
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





    def set_single_laser(self, which_laser, frequency, do_switch = False, wait_time = None):
        
        if which_laser == 422:
            channel = 5
        elif which_laser == 390:
            channel = 6                

        if do_switch:
            switch = 1
        else:
            switch = 0

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('192.168.42.136', 63700)

        print('Sending new setpoint: ' + str(frequency))
        sock.connect(server_address)
        
        message = "{0:1d},{1:.9f},{2:1d},{3:3d}".format(int(channel), float(frequency), int(switch), int(wait_time))
    
        sock.sendall(message.encode())
        
        sock.close()

        time.sleep(2*wait_time/1000.0)
       
        return



    def run(self):
       
        # Set voltage of the mesh
        #self.set_mesh_voltage(self.mesh_voltage)

        # Lock the frequency of 422 and 390 to the initial point

        time.sleep(10)

        self.set_single_laser(422, self.frequency_422, do_switch = True, wait_time = self.relock_wait_time)
        self.set_single_laser(390, self.frequency_390 + self.min_freq*1e6/1e12, do_switch = True, wait_time = self.relock_wait_time)

        time.sleep(3)

        # Scan frequencies of 390 and store the result
        self.scan_results = [0.0] * len(self.scan_values)
        
        for i in range(len(self.scan_values)):

            self.scheduler.pause() # allows for "terminate instances" functionality
            
            print("{0}/{1}: {2:.6f}".format(i, len(self.scan_values), self.scan_values[i]))
           
            
            # set laser frequencies
            # re-lock 422
            if i % self.relock_422_steps == 0:
                print('Relocking 422 ..')
                self.set_single_laser(422, self.frequency_422, do_switch = True, wait_time = self.relock_wait_time)
                self.set_single_laser(390, self.scan_values[i], do_switch = True, wait_time = self.relock_wait_time)
            else:
                self.set_single_laser(390, self.scan_values[i], wait_time = self.lock_wait_time)
            
            # to get more averages repeat the 500 averages and average again
            avg_counts = 0
            for k in range(self.no_of_repeats):
                # take <no_of_averages> data points and repeat <no_of_repeats> times
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


        self.set_single_laser(390, self.frequency_390, do_switch = True, wait_time = self.relock_wait_time)



