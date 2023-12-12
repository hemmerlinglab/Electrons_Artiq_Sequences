from artiq.experiment import *
#import artiq.coredevice.sampler as splr
import numpy as np
import os

#####################################################################
# Functions with decorators
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

                #delay(self.load_time * us)
                
                #delay(self.detection_time * us)

                # detect for 5 us
                #t_start = now_mu()
                #t_end = self.ttl3.gate_rising(20 * us)                

                delay(1*us)

                tload_start = now_mu()
                tload_end = self.ttl3.gate_rising(20*us)

                delay((self.detection_time-20)*us)

                t_start = now_mu()
                t_end = self.ttl3.gate_rising(20*us)
                

            with sequential:

                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time * us)

            # Extraction pulse
            with sequential:
                
                #delay(self.load_time * us)
                
                delay(self.extraction_time * us)
                self.ttl6.pulse(1*us)

            # Tickling pulse
            with sequential:
                
                #delay(self.load_time * us)
                
                delay(5 * us)
                
                self.ttl8.pulse(self.tickle_pulse_length * us)

        read_only_timestamps(self, tload_start, tload_end, 'timestamps_loading')
        read_only_timestamps(self, t_start, t_end, 'timestamps')

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

                #delay(self.load_time * us)
                
                t_start = now_mu()
                t_end = self.ttl3.gate_rising(self.detection_time*us)

            with sequential:

                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time * us)

            # Extraction pulse
            with sequential:
                
                #delay(self.load_time * us)
                
                delay(self.extraction_time * us)
                self.ttl6.pulse(1*us)

            # Tickling pulse
            with sequential:
                
                #delay(self.load_time * us)
                
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



