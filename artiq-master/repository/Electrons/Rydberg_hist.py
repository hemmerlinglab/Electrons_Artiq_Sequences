from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *

class Rydberg_hist(EnvExperiment):
    
    def build(self):
        
        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
#        self.setattr_device('ttl8') # Triggers AOM pulse
        self.setattr_device('ttl11') # Triggers extraction pulse
        self.setattr_device('scheduler')
        self.setattr_device('zotino0')

        # Setting the lock frequency for 422 and the scan range for 390
        self.my_setattr('frequency_422', NumberValue(default=709.078540,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('frequency_390', NumberValue(default=768.824120,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('min_freq', NumberValue(default=-1000,unit='MHz',scale=1,ndecimals=6,step=1))
        self.my_setattr('max_freq', NumberValue(default=1000,unit='MHz',scale=1,ndecimals=6,step=1))
        self.my_setattr('steps', NumberValue(default=10,unit='steps to scan',scale=1,ndecimals=0,step=1))
        
        # Setting laser lock parameters
        self.my_setattr('relock_422_steps', NumberValue(default=3,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('relock_wait_time', NumberValue(default=1000,unit='ms',scale=1,ndecimals=1,step=1))
        self.my_setattr('lock_wait_time', NumberValue(default=1000,unit='ms',scale=1,ndecimals=1,step=1))

        # Setting mesh voltage
        self.my_setattr('mesh_voltage', NumberValue(default=150,unit='V',scale=1,ndecimals=0,step=1))

        # Setting experiment parameters
        self.my_setattr('no_of_repeats', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.my_setattr('detection_time', NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))

        # Setting histogram parameters
        self.setattr_argument('number_of_bins', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('max_no_of_timestamps', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))


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
        
        mesh_voltage_dc_channel = 31

        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(mesh_voltage_dc_channel, 65000)
        self.zotino0.write_dac(mesh_voltage_dc_channel, 1.0/200.0 * voltage)
        self.zotino0.load()


    def prepare(self):
        
        # Calculate the frequencies for scanning
        self.scan_values = self.frequency_390 + 1e-6 * np.linspace(self.min_freq, self.max_freq, self.steps)
        
        #self.MAX_NO_OF_TIMESTAMPS = 1000

        # Create the dataset of the result
        self.set_dataset('set_points', [0] * len(self.scan_values), broadcast=True)
        self.set_dataset('act_freqs', [0] * len(self.scan_values), broadcast=True)
        self.set_dataset('scan_result', [ [0.0] * self.max_no_of_timestamps ] * len(self.scan_values), broadcast=True)
        
        # Set the data going to save
        self.data_to_save = [{'var' : 'set_points', 'name' : 'set_points'},
                             {'var' : 'act_freqs', 'name' : 'act_freqs'},
                             {'var' : 'scan_result', 'name' : 'counts'}]

        # save sequence file name
        self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})

        get_basefilename(self)

        self.core.reset() # Reset the core

        self.set_dataset('bin_times', [0], broadcast=True) # use to store timestamps of events, place 0 to be consistent with reset code
        self.hist_data = [] # use to store timestamp datas of up to max_loop_data times


    def analyze(self):
        
        print('saving data...')
        save_all_data(self)

        # overwrite config file with complete configuration
        self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
        save_config(self.basefilename, self.config_dict)

        add_scan_to_list(self)
        
        print('Scan ' + self.basefilename + ' finished.')
        print('Scan finished.')

#########################################################
#####              Histogram Functions              #####
#########################################################

    def make_histogram(self):
        extract = list(self.get_dataset('bin_times'))

        ## use extract[1:len(extract)] to discard the 0 placed when doing initialization and reset
        #if loop < self.max_loop_data:
        self.hist_data.append(extract[1:len(extract)])
        #else:
        #    self.hist_data[loop % self.max_loop_data] = extract[1:len(extract)]
        
        flatten_data = sum(self.hist_data, []) # flatten 2D list self.hist_data to 1D list
        a, b = np.histogram(flatten_data, bins = np.linspace(0, self.dete#        self.set_single_laser(390, self.frequency_390 + self.min_freq*1e6/1e12, do_switch = True, wait_time = self.relock_wait_time)
ction_time, self.number_of_bins))
        
        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)

        return

    @kernel
    def read_timestamps(self, t_start, t_end):
        
        self.set_dataset('bin_times', [0], broadcast=True) # reset with empty list is not allowed, so place a zero in it
        tstamp = self.ttl3.timestamp_mu(t_end)
        while tstamp != -1:
            timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
            timestamp_us = timestamp * 1e6
            
            self.append_to_dataset('bin_times', timestamp_us) # store the timestamps in microsecond
            tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

        # display
        self.make_histogram()
        return

######################################################
#####         End of Histogram Functions         #####
######################################################

    def set_single_laser(self, which_laser, frequency, do_switch = False, wait_time = None):
        
        return

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


    @kernel
    def run_sequence(self):

        self.core.break_realtime()

        with parallel:
            with sequential:

                delay(1*us)
                # extraction pulse
                self.ttl11.pulse(20*us)

            with sequential:
                
                t_start = now_mu()
                t_end = self.ttl3.gate_rising(self.detection_time*us)
                
                self.read_timestamps(t_start, t_end)

        return


    def run(self):
       
        # Set voltage of the mesh
        self.set_mesh_voltage(self.mesh_voltage)

        # Lock the frequency of 422 and 390 to the initial point
        self.set_single_laser(422, self.frequency_422, do_switch = True, wait_time = self.relock_wait_time)
        self.set_single_laser(390, self.frequency_390, do_switch = True, wait_time = self.relock_wait_time)

        time.sleep(3)

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
            
            self.hist_data = [] # histogram reset
            len_bin_times = np.zeros(self.no_of_repeats) # record the number of events in each repeat
            save_bin_times = np.zeros(self.max_no_of_timestamps)

            for j in range(self.no_of_repeats):

                self.run_sequence()

                # Save data
                extract = list(self.get_dataset('bin_times'))
                my_bin_times = extract[1:len(extract)]
                len_bin_times[j] = len(my_bin_times)
                save_bin_times[len_bin_times[0:j].sum():len_bin_times[0:j+1]] = my_bin_times

            #self.run_sequence()

            #extract = list(self.get_dataset('bin_times')) # of variable length
            #my_bin_times = extract[1:len(extract)]

            #save_bin_times[0:len(my_bin_times)] = my_bin_times

            self.mutate_dataset('scan_result', i, save_bin_times)

            # read laser frequencies
            self.wavemeter_frequencies = get_laser_frequencies()
            

            self.mutate_dataset('act_freqs', i, self.wavemeter_frequencies)
            self.mutate_dataset('set_points', i, self.scan_values[i])

        self.set_single_laser(390, self.frequency_390, do_switch = True, wait_time = self.relock_wait_time)

