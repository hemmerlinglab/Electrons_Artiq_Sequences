from artiq.experiment import *
import numpy as np
import socket
import time
import sys

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *
from dc_electrodes import *

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/drivers")
from bk_4053 import BK4053
from rs_scan import RS

class Boerge_Trapped_Electrons_Counting(EnvExperiment):

    def build(self):

        self.ext_pulser  = BK4053() # Two pulsers: BK4053 (negative pulse) and DG4162 (positive pulse)
        self.RF_driver = RS()

        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')
        self.setattr_device('ttl3') # For inputing MCP signals
        self.setattr_device('ttl4') # For sending beginning signal
        self.setattr_device('ttl6') # For triggering RF
        self.setattr_device('ttl8') # For triggering tickle pulse
        self.setattr_device('ttl11') # For triggering AOM and extraction pulse
        self.setattr_device('scheduler')
        self.setattr_device('zotino0') # For setting voltages of the mesh and DC electrodes

        # Setting mesh voltage
        self.setattr_argument('mesh_voltage', NumberValue(default=350,unit='V',scale=1,ndecimals=0,step=1))

        # Setting parameters for the applet display
        self.setattr_argument('time_count', NumberValue(default=200,unit='number of counts',scale=1,ndecimals=0,step=1))

        # Setting parameters for the histogram
        self.setattr_argument('bin_width', NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=.1))      
        self.setattr_argument('histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1))
        
        # Setting time parameters of the experiment
        #self.setattr_argument('detection_time', NumberValue(default=250,unit='us',scale=1,ndecimals=0,step=1))
        self.setattr_argument('load_time', NumberValue(default=200,unit='us',scale=1,ndecimals=0,step=1))
        self.setattr_argument('extraction_time', NumberValue(default=240,unit='us',scale=1,ndecimals=0,step=1))
        self.setattr_argument('no_of_repeats', NumberValue(default=10000,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('tickle_pulse_length', NumberValue(default=10,unit='us',scale=1,ndecimals=1,step=1))
        self.setattr_argument('flip', EnumerationValue(['Y', 'N'],default='N'))

        # Setting RF configurations
        self.setattr_argument('RF_frequency',NumberValue(default=1.5762,unit='GHz',scale=1,ndecimals=4,step=.0001))
        self.setattr_argument('RF_amplitude',NumberValue(default=5,unit='dBm',scale=1,ndecimals=1,step=.1))

        # Setting DC configurations
        self.setattr_argument('Ex', NumberValue(default=0.0,unit='',scale=1,ndecimals=2,step=.01))
        self.setattr_argument('Ey', NumberValue(default=0.0,unit='',scale=1,ndecimals=2,step=.01))
        self.setattr_argument('Ez', NumberValue(default=0.0,unit='',scale=1,ndecimals=2,step=.01))

        self.setattr_argument('U1', NumberValue(default=0.0,unit='',scale=1,ndecimals=2,step=.01))
        self.setattr_argument('U2', NumberValue(default=-0.2,unit='',scale=1,ndecimals=2,step=.01))
        self.setattr_argument('U3', NumberValue(default=0.0,unit='',scale=1,ndecimals=2,step=.01))
        self.setattr_argument('U4', NumberValue(default=0.0,unit='',scale=1,ndecimals=2,step=.01))
        self.setattr_argument('U5', NumberValue(default=0.0,unit='',scale=1,ndecimals=2,step=.01))

        # Filp the trap
        if self.flip == 'N':
            self.electrodes = Electrodes()
        else:
            self.electrodes = Flipped_Electrodes()

        return


    @kernel
    def set_mesh_voltage(self, voltage):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(31, 65000)
        self.zotino0.write_dac(31, 1.0/198.946 * (voltage + 14.6027))
        self.zotino0.load()

        return


    @kernel
    def set_electrode_voltages(self, channel_list, voltage_list):
        
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


    def prepare(self):

        self.detection_time = int(self.extraction_time - 5*us)
        
        # Create the dataset of the result
        self.set_dataset('timestamps', [], broadcast=True)
        self.set_dataset('count_tot', [0.0] * self.time_count, broadcast=True)

        self.hist_data = []

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
        print('Vector Defined!')
        (chans, voltages) = self.electrodes.getVoltageMatrix(self.multipole_vector)
        print('Voltages Computed!')
        print('chans:', chans)
        print('voltages:', voltages)
        self.set_electrode_voltages(chans, voltages)
        print('Electrode voltages applied!')

        # Settings of the R&S SMB100A RF generator (trap RF drive)
        self.RF_driver.set_freq(self.RF_frequency*1e+9)
        self.RF_driver.set_ampl(self.RF_amplitude)

        # set the extraction pulse
        ext_pulser_freq = 1e6 / (self.detection_time+100)
        self.ext_pulser.set_carr_freq(2, ext_pulser_freq)
        self.ext_pulser.set_carr_delay(2, (self.extraction_time+0.15) * 1e-6)

        # Set mesh voltages
        self.set_mesh_voltage(self.mesh_voltage)
        print('Mesh voltage already set!')
        print('Presets done!')
        
        self.core.reset() # Reset the core


    def make_histogram(self):
        
        # for display
        extract = list(self.get_dataset('timestamps'))
        self.hist_data = extract[1:len(extract)]
        number_of_bins = int(self.detection_time / self.bin_width)
        a, b = np.histogram(self.hist_data, bins = np.linspace(0, self.detection_time, number_of_bins))
        
        self.set_dataset('hist_ys', a, broadcast=True)
        self.set_dataset('hist_xs', b, broadcast=True)

        return


    @kernel
    def read_timestamps(self, t_start, t_end, i):

        if (i+1) % self.histogram_refresh != 0:
            tstamp = self.ttl3.timestamp_mu(t_end)
            while tstamp != -1:
                timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
                timestamp_us = timestamp * 1e6
                self.append_to_dataset('timestamps', timestamp_us) # store the timestamps in microsecond
                tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

        else:
            self.make_histogram()

        return

    @kernel
    def read_only_timestamps(self, t_start, t_end, i):

        tstamp = self.ttl3.timestamp_mu(t_end)
        while tstamp != -1:
            timestamp = self.core.mu_to_seconds(tstamp) - self.core.mu_to_seconds(t_start)
            timestamp_us = timestamp * 1e6
            self.append_to_dataset('timestamps', timestamp_us) # store the timestamps in microsecond
            tstamp = self.ttl3.timestamp_mu(t_end) # read the timestamp of another event

        return



    @kernel
    def run_histogram(self):
        
        ind_count = 0
        # Time Sequence
        for i in range(self.no_of_repeats):

            self.core.break_realtime()

            with parallel:

                # Overall start TTL of sequence
                self.ttl4.pulse(2*us)

                # Gate counting to count MCP pulses
                with sequential:

                    #delay(self.detection_time * us)

                    ## detect for 5 us
                    #t_start = now_mu()
                    #t_end = self.ttl3.gate_rising(20 * us)

                    t_start = now_mu()
                    t_end = self.ttl3.gate_rising(self.detection_time*us)

                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time*us)

                # Extraction pulse
                with sequential:
                    delay(self.extraction_time * us)
                    self.ttl6.pulse(1*us)

                # Tickling pulse
                with sequential:
                    delay(self.load_time * us)
                    delay(5 * us)
                    self.ttl8.pulse(self.tickle_pulse_length * us)

            self.read_timestamps(t_start, t_end, i)



    @kernel
    def count_events(self):
        
        ind_count = 0
        # Time Sequence
        for i in range(self.no_of_repeats):

            self.core.break_realtime()

            with parallel:

                # Overall start TTL of sequence
                self.ttl4.pulse(2*us)

                # Gate counting to count MCP pulses
                with sequential:

                    delay(self.detection_time * us)

                    # detect for 5 us
                    t_start = now_mu()
                    t_end = self.ttl3.gate_rising(20 * us)

                    #t_start = now_mu()
                    #t_end = self.ttl3.gate_rising(self.detection_time*us)

                # Loading: TTL to switch on AOM
                self.ttl11.pulse(self.load_time*us)

                # Extraction pulse
                with sequential:
                    delay(self.extraction_time * us)
                    self.ttl6.pulse(1*us)

                # Tickling pulse
                with sequential:
                    delay(self.load_time * us)
                    delay(5 * us)
                    self.ttl8.pulse(self.tickle_pulse_length * us)

            self.read_only_timestamps(t_start, t_end, i)



    def run(self):

        counter = 0

        while True:

            self.scheduler.pause()

            # extraction
            #self.run_histogram()

            
            if False:
                # update data
                xs = self.get_dataset('hist_xs')
                ys = self.get_dataset('hist_ys')
                ind_l = (xs > (self.extraction_time - 2 / self.bin_width))[:-1]
                ind_u = (xs < (self.extraction_time + 4 / self.bin_width))[:-1]
                cts = np.sum(ys[ind_l*ind_u])
                self.mutate_dataset('count_tot', counter % self.time_count, cts)

            
            self.count_events()

            extract = list(self.get_dataset('timestamps'))

            self.mutate_dataset('count_tot', counter % self.time_count, len(extract))

            self.set_dataset('timestamps', [], broadcast=True)
            counter += 1



