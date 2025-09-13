from artiq.experiment import *
import numpy as np
import socket

from helper_functions import calculate_input_voltage

###########################################################
##  Control Widgets  ######################################
###########################################################

# ===================  Laser Control  =================== #
"""
# ---- Temporary Notes ---- #
What I need to do to build laser control into the script?
1. Update with input parameters, instead of self attributes
2. In prepare stage, send frequency setpoint defined by self
   attributes to the laser lock desktop
3. In analyze stage, send frequency setpoint defined by self
   attributes to the laser lock desktop to pull it back
4. Do not modify self attributes for laser frequencies during
   experiment run

Tips:
IP Address for laser lock desktop (1041_RGA): 192.168.42.26 / 192.168.42.136
PORT Number used in the laser lock program: 63700
Expected Format for the laser lock program: 

Write a code to test out the actual address for socket
"""
def set_laser_frequency(self, laser, frequency):

    if laser not in [422, 390]:
        raise ValueError(f"We only have laser 422 and 390, received {laser}!")

    return

# =============  Extraction Pulse Control  ============= #
def set_extraction_pulse(self):

    # Set extraction pulse frequency (for robustness)
    ext_freq = 1e6 / (self.detection_time+100)
    self.ext_pulser.set_carr_freq(2, ext_freq)
    self.ext_pulser.set_carr_delay(2, (self.load_time+self.wait_time+0.15) * 1e-6)

    # Set extraction pulse length
    self.ext_pulser.set_carr_width(2, ext_freq, self.ext_pulse_length * 1e-9)

    # Set extraction pulse amplitude
    self.ext_pulser.set_carr_ampl(2, self.ext_pulse_amplitude)

    return

# ===========  AOM Modulation Pulse Control  =========== #
def set_loading_pulse(self):
    
    ext_freq = 1e6 / (self.detection_time+100)

    self.ext_pulser.set_carr_freq(1, ext_freq)
    self.ext_pulser.set_carr_width(1, ext_freq, self.load_time * 1e-6)

    return

# ====  Calculate Detection Time Based on Set Times  ==== #
def update_detection_time(self):

    # detect all the time + 10 us extraction pulse
    self.detection_time = self.load_time + self.wait_time + self.ext_pulse_length // 1000 + 10

    return

# ===============  DC Multipoles Control  =============== #
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
    (chans, voltages) = self.electrodes.get_control_voltage(self.multipole_vector)

    # set Zotino voltages
    set_electrode_voltages(self, chans, voltages)

    return

# ================  DC Voltages Control  ================ #
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

# ===============  Mesh Voltage Control  =============== #
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

# ===============  MCP Voltages Control  =============== #
def set_MCP_voltages(self, front_voltage):

    '''This function takes adjusted voltages, remember
    to divide the setpoint by 500 and make calibration
    adjustment when using.'''

    chan = [28, 29, 30]

    vols = [0, 0, 0]
    vols[0] = calculate_input_voltage(chan[0], front_voltage/500, use_amp=False)
    vols[1] = calculate_input_voltage(chan[1], (front_voltage+2000)/500, use_amp=False)
    vols[2] = calculate_input_voltage(chan[2], (front_voltage+2200)/500, use_amp=False)

    #print(chan, vols)
    set_electrode_voltages(self, chan, vols)
    
    return 0

###########################################################
##  Experiment Sequences  #################################
###########################################################

# =======  Experiment Sequences - histogram off  ======= #
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

                #delay((self.detection_time-self.load_time)*us)      # Old Logic
                delay((self.wait_time-3)*us)

                t_start = now_mu()
                #t_end = self.ttl3.gate_rising(10*us)                # Old Logic
                t_end = self.ttl3.gate_rising((self.ext_pulse_length // 1000 + 8)*us)
                
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

        read_only_timestamps(self, tload_start, t_end, 'timestamps')

    return

@kernel
def read_only_timestamps(self, t_start, t_end, which_data_set):

    tstamp = self.ttl3.timestamp_mu(t_end)
    while tstamp != -1:
        timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
        timestamp_us = timestamp * 1e6
        self.append_to_dataset(which_data_set, timestamp_us) # store the timestamps in microsecond
        tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

    return

# ========  Experiment Sequences - histogram on  ======== #
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

# =============  Calculate Histogram Data  ============= #
def make_histogram(self):
    
    # for display
    extract = list(self.get_dataset('timestamps'))
    self.hist_data = extract[1:len(extract)]
    number_of_bins = int(self.detection_time / self.bin_width) + 1
    a, b = np.histogram(self.hist_data, bins = np.linspace(0, self.detection_time, number_of_bins))
    
    self.set_dataset('hist_ys', a, broadcast=True)
    self.set_dataset('hist_xs', b, broadcast=True)

    return

