from artiq.experiment import kernel, delay, now_mu, us, ms, parallel, sequential
import numpy as np
import time

from helper_functions import calculate_input_voltage, calculate_Vsampler, calculate_HighV, calculate_Vin, safe_check

###########################################################
##  Control Widgets  ######################################
###########################################################

# ==============  Recording and Validating ============== #
def record_laser_frequencies(self, idx, tol = 1e-5):
    """
    Fetch Last Frequencies of each laser from Laser Lock GUI and record them into dataset.
    When failed to fetch frequency, 0.0 will be returned according to the function.
    """

    freq_422 = self.laser.get_frequency(422)
    freq_390 = self.laser.get_frequency(390)

    self.mutate_dataset('last_frequency_422', idx, freq_422)
    self.mutate_dataset('last_frequency_390', idx, freq_390)

    status_422 = (abs(freq_422 - self.frequency_422) <= tol)
    status_390 = (abs(freq_390 - self.frequency_390) <= tol)

    return status_390, status_422

def record_RF_amplitude(self, idx):

    ampl = self.rf.get_amplitude()
    self.mutate_dataset('act_RF_amplitude', idx, ampl)
    
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
    self.ext_pulser.set_carr_ampl(2, self.ext_pulse_level)
    
    # Parts to ensure
    self.ext_pulser.set_burst_mode(2, True)

    return

# ===========  AOM Modulation Pulse Control  =========== #
def set_loading_pulse(self):
    
    ext_freq = 1e6 / (self.detection_time+100)

    # Parts to set
    self.ext_pulser.set_carr_freq(1, ext_freq)
    self.ext_pulser.set_carr_width(1, ext_freq, self.load_time * 1e-6)

    # Parts to ensure
    self.ext_pulser.set_carr_delay(1, 0.0)
    self.ext_pulser.set_carr_ampl(1, 1.0)
    self.ext_pulser.set_carr_offset(1, 0.5)
    self.ext_pulser.set_burst_mode(2, True)
    
    # Make sure the pulser is on
    # both channel is switched here because we do not want this recurring
    self.ext_pulser.on(1)
    self.ext_pulser.on(2)

    return

# ====  Calculate Detection Time Based on Set Times  ==== #
def update_detection_time(self):

    # detect all the time + 10 us extraction pulse
    # in trapping mode, unit is us, but in counting mode, unit is ms
    if self.mode == 'Trapping':
        self.detection_time = self.load_time + self.wait_time + self.ext_pulse_length // 1000 + 10

    return

# =============  General Zotino Controller  ============= #
@kernel
def zotino_initialization(self):

    self.core.break_realtime()
    self.zotino0.init()
    delay(200*us)

    return

@kernel
def zotino_write(self, channel, voltage):

    self.core.break_realtime()
    self.zotino0.write_gain_mu(channel, 65000)
    delay(200*us)
    self.zotino0.write_dac(channel, voltage)
    self.zotino0.load()
    delay(200*us)

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
# This function must be standalone instead of calling zotino_write
# because otherwise it would be extremely slow (causing 5s overhead)
@kernel
def set_electrode_voltages(self, channel_list, voltage_list):
    
    self.core.break_realtime()

    for k in range(len(channel_list)):
        self.zotino0.write_gain_mu(channel_list[k], 65000)
        delay(100*us)
        self.zotino0.write_dac(channel_list[k], voltage_list[k])
        self.zotino0.load()
        delay(200*us)

    return

# ===============  Mesh Voltage Control  =============== #
def set_mesh_voltage(self, voltage):

    CHANNEL_MESH = 31
    control_signal = 1.0/198.946 * (voltage + 14.6027)
    zotino_write(self, CHANNEL_MESH, control_signal)

    return

# ============  Threhold Voltages Control  ============= #
def set_threshold_voltage(self, voltage):

    CHANNEL_THRES = 27
    control_signal = calculate_input_voltage(CHANNEL_THRES, voltage, use_amp=False)
    zotino_write(self, CHANNEL_THRES, control_signal)

    return

# ===============  MCP Voltages Control  =============== #
def set_MCP_voltages(self, val):

    '''This function takes adjusted voltages, remember
    to divide the setpoint by 500 and make calibration
    adjustment when using.'''

    chan = [28, 29, 30]
    vols = [0.0, 0.0, 0.0]

    MCP_setpoint = [val, val+2000, val+2200]
    current_MCP_voltage = get_MCP_voltages(self)

    if safe_check(MCP_setpoint, mode="setpoint"):
        raise ValueError("Unsafe setpoint!")
    if safe_check(current_MCP_voltage):
        raise RuntimeError("Initial state is already unsafe!")

    first_cycle = True

    while current_MCP_voltage != MCP_setpoint:
        sleep_time = 5
        for i, vs in enumerate(MCP_setpoint):
            if abs(vs - current_MCP_voltage[i]) < 50:
                current_MCP_voltage[i] = MCP_setpoint[i]
            elif vs - current_MCP_voltage[i] >= 50:
                current_MCP_voltage[i] += 50
                sleep_time = 10
            elif vs - current_MCP_voltage[i] <= -50:
                current_MCP_voltage[i] -= 50

        if safe_check(current_MCP_voltage):
            raise RuntimeError("Equipment destroyed!")

        if not first_cycle: time.sleep(sleep_time)
        first_cycle = False

        print(f"[MCP] Applying MCP Voltage: {current_MCP_voltage:.3f}, {current_MCP_voltage:.3f}, {current_MCP_voltage:.3f}")

        for i, v in enumerate(current_MCP_voltage):
            #print(v)
            vols[i] = calculate_Vin(i, v)

        #print(chan, vols)
        set_electrode_voltages(self, chan, vols)
    
    return

@kernel
def sampler_read(self):

    self.core.break_realtime()
    self.sampler0.init()
    delay(200*us)
    
    readings = [0.0]*8
    self.sampler0.sample(readings)
    self.set_dataset("sampler_voltages", readings, broadcast=True)
    self.core.break_realtime()

def get_MCP_voltages(self):

    sampler_read(self)

    sampler_voltages = self.get_dataset("sampler_voltages")[:3]
    control_voltages = [0.0, 0.0, 0.0]
    high_voltages = [0.0, 0.0, 0.0]

    for i in range(len(sampler_voltages)):
        control_voltages[i] = calculate_Vsampler(i, sampler_voltages[i])

    for i in range(len(control_voltages)):
        high_voltages[i] = calculate_HighV(i, control_voltages[i])

    self.set_dataset("MCP_voltages", high_voltages, broadcast=True)

    return high_voltages

###########################################################
##  Experiment Sequences  #################################
###########################################################

# =======  Experiment Sequences - bare counting  ======= #
@kernel
def bare_counting(self):

    self.core.break_realtime()

    # Use detection_time as detection time, standalone mode for counting
    # unit is ms (us for trapping mode)
    ev = self.ttl3.gate_rising(self.detection_time * ms)

    return self.ttl3.count(ev)

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

    tstamp = self.ttl3.timestamp_mu(t_end)
    while tstamp != -1:
        timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
        timestamp_us = timestamp * 1e6
        self.append_to_dataset('timestamps', timestamp_us) # store the timestamps in microsecond
        tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

    if ((i+1) % self.histogram_refresh == 0) or ((i+1) == self.no_of_repeats):
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

