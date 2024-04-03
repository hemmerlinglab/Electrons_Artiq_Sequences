from artiq.experiment import *
#import artiq.coredevice.sampler as splr
import numpy as np
import os
from helper_functions import adjust_set_volt


############################################################
def set_extraction_pulse(self):

    ext_freq = 1e6 / (self.detection_time+100)
    self.ext_pulser.set_carr_freq(2, ext_freq)
    self.ext_pulser.set_carr_delay(2, (self.load_time+self.wait_time+0.15) * 1e-6)

    return

def set_loading_pulse(self):
  
    # set the loading pulse
    
    ext_freq = 1e6 / (self.detection_time+100)

    self.ext_pulser.set_carr_freq(1, ext_freq)
    self.ext_pulser.set_carr_width(1, ext_freq, self.load_time * 1e-6)

    return


############################################################

def update_detection_time(self):

    # Detect during the extraction pulse
    if self.show_histogram:
        # detect all the time + 10 us extraction pulse
        self.detection_time = self.load_time + self.wait_time + 10
    else:
        # detect for short time starting 5 us before extraction pulse
        self.detection_time = self.load_time + self.wait_time - 3

    return

############################################################

def set_multipoles(self):

    # Compute the voltages of DC electrodes we want

    self.multipole_vector = {
            'Ex' : self.Ex, #0,
            'Ey' : self.Ey, #0,
            'Ez' : self.Ez, #0,
            'U1' : self.U1, #0,
            'U2' : self.U2, #-0.69,
            'U3' : self.U3, #0,
            'U4' : self.U4, #0,
            'U5' : self.U5  #0
        }

    # get dc voltages
    (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)

    # adjust voltage setpoint using calibrating data
    for i in range(len(chans)-1):
        voltages[i+1] = adjust_set_volt(chans[i+1], voltages[i+1])

    # set Zotino voltages
    set_electrode_voltages(self, chans, voltages)

    return


#####################################################################

@kernel
def set_mesh_voltage(self, voltage):

    #print('Setting mesh voltage')
    
    self.core.break_realtime()
    self.zotino0.init()
    delay(200*us)
    self.zotino0.write_gain_mu(31, 65000)
    self.zotino0.write_dac(31, 1.0/198.946 * (voltage + 14.6027))
    self.zotino0.load()

    return


#####################################################################

@kernel
def set_electrode_voltages(self, channel_list, voltage_list):

    #print('Setting DC electrode voltages')
    
    voltage = 0

    self.core.reset()
    self.core.break_realtime()
    self.zotino0.init()
    delay(200*us)
            
    for k in range(len(channel_list)):

        self.zotino0.write_gain_mu(channel_list[k], 65000)
        self.zotino0.load()
        delay(200*us)
        self.zotino0.write_dac(channel_list[k], voltage_list[k])
        self.zotino0.load()
        delay(200*us)

    return


#####################################################################

def set_MCP_voltages(self, front_voltage):

    '''This function takes adjusted voltages, remember
    to divide the setpoint by 500 and make calibration
    adjustment when using.'''

    chan = [28, 29, 30]

    vols = [0, 0, 0]
    vols[0] = adjust_set_volt(chan[0], front_voltage/500)
    vols[1] = adjust_set_volt(chan[1], (front_voltage+2000)/500)
    vols[2] = adjust_set_volt(chan[2], (front_voltage+2200)/500)

    #print(chan, vols)
    set_electrode_voltages(self, chan, vols)
    
    return 0


#####################################################################

@kernel
def count_events(self):
    
    ind_count = 0
    # Time Sequence
    for i in range(self.no_of_repeats):

        self.core.break_realtime()

        with parallel:

            with sequential:
                # Overall start TTL of sequence
                self.ttl4.pulse(2*us)

            # Gate counting to count MCP pulses
            with sequential:             

                tload_start = now_mu()
                tload_end = self.ttl3.gate_rising(self.load_time*us)

                delay((self.detection_time-self.load_time)*us)

                t_start = now_mu()
                t_end = self.ttl3.gate_rising(10*us)
                
            with sequential:

                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time * us)

            # Extraction pulse
            with sequential:
                
                delay((self.load_time+self.wait_time) * us)
                self.ttl6.pulse(1*us)

            # Tickling pulse
            with sequential:
                
                delay(self.load_time * us)
                
                delay(5 * us)
                
                self.ttl8.pulse(self.tickle_pulse_length * us)

        #read_only_timestamps(self, tload_start, tload_end, 'timestamps_loading')
        read_only_timestamps(self, tload_start, t_end, 'timestamps')

    return


#####################################################################

@kernel
def count_histogram(self):
    
    ind_count = 0
    # Time Sequence
    for i in range(self.no_of_repeats):

        self.core.break_realtime()

        with parallel:

            with sequential:

                # Overall start TTL of sequence
                self.ttl4.pulse(2*us)

            # Gate counting to count MCP pulses
            with sequential:

                t_start = now_mu()
                t_end = self.ttl3.gate_rising(self.detection_time*us)

            with sequential:

                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time * us)

            # Extraction pulse
            with sequential:
                
                delay((self.load_time+self.wait_time) * us)
                self.ttl6.pulse(1*us)

            # Tickling pulse
            with sequential:
                
                delay(self.load_time * us)
                
                delay(5 * us)
                
                self.ttl8.pulse(self.tickle_pulse_length * us)

        read_histogram_timestamps(self, t_start, t_end, i)

    return


#####################################################################

@kernel
def read_only_timestamps(self, t_start, t_end, which_data_set):

    tstamp = self.ttl3.timestamp_mu(t_end)
    while tstamp != -1:
        timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
        timestamp_us = timestamp * 1e6
        self.append_to_dataset(which_data_set, timestamp_us) # store the timestamps in microsecond
        tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

    return


#####################################################################

@kernel
def read_histogram_timestamps(self, t_start, t_end, i):

    if (i+1) % self.histogram_refresh != 0:
        tstamp = self.ttl3.timestamp_mu(t_end)
        while tstamp != -1:
            timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
            timestamp_us = timestamp * 1e6
            self.append_to_dataset('timestamps', timestamp_us) # store the timestamps in microsecond
            tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

    else:
        make_histogram(self)

    return


############################################################

def make_histogram(self):
    
    # for display
    extract = list(self.get_dataset('timestamps'))
    self.hist_data = extract[1:len(extract)]
    number_of_bins = int(self.detection_time / self.bin_width)
    a, b = np.histogram(self.hist_data, bins = np.linspace(0, self.detection_time, number_of_bins))
    
    self.set_dataset('hist_ys', a, broadcast=True)
    self.set_dataset('hist_xs', b, broadcast=True)

    return



