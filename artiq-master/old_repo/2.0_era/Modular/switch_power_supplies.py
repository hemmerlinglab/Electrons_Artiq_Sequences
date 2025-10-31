from artiq.experiment import *
import numpy as np
import time

import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import calculate_input_voltage

class Switch_power_supply(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('zotino0')

        self.setattr_argument('switch', EnumerationValue(['On','Off'],default='On'))
        self.setattr_argument('front_voltage', NumberValue(default=200,unit='V',scale=1,ndecimals=0,step=1))

        self.channels = [28, 29, 30]
        self.control_voltages = [0, 0, 0]
        
    @kernel
    def set_voltages(self):
        
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)

        for i in range(len(self.channels)):
            self.zotino0.write_gain_mu(self.channels[i], 65000)
            self.zotino0.load()
            delay(200*us)
            self.zotino0.write_dac(self.channels[i], self.control_voltages[i])
            self.zotino0.load()
            delay(200*us)

        return

    def run(self):

        f_ind = self.front_voltage // 100
        
        if self.switch == 'On':

            for i in range(f_ind+23):

                time.sleep(20)

                voltages = [0, 0, 0]
                if i < f_ind:
                    voltages = [(i+1)*100] * 3
                elif i < (f_ind + 20):
                    voltages[0] = self.front_voltage
                    voltages[1] = (i+1)*100 - 4
                    voltages[2] = (i+1)*100
                else:
                    voltages[0] = self.front_voltage
                    voltages[1] = self.front_voltage + 2000 - 6
                    voltages[2] = min((i+1)*100, self.front_voltage+2200)

                for i in range(len(voltages)):
                    self.control_voltages[i] = calculate_input_voltage(self.channels[i], voltages[i]/500, use_amp=False)
                    print(f"Sending control signal {self.control_voltages[i]:.2f} to channel {self.channels[i]} for achieving voltage {voltages[i]}")
                
                print('\n')
                self.set_voltages()
            
        else:
            
            print('Setting voltages to (' + str(self.front_voltage) + ', ' + str(self.front_voltage+2000) + ', ' + str(self.front_voltage+2200) + ')')
            voltages = [self.front_voltage, self.front_voltage+2000, self.front_voltage+2200]
            for i in range(len(voltages)):
                #print(self.channels[i], voltages[i])
                self.control_voltages[i] = calculate_input_voltage(self.channels[i], voltages[i]/500, use_amp=False)
            self.set_voltages()

            for i in range(f_ind+23):

                time.sleep(10)

                if i < 2:
                    voltages[2] = voltages[2] - 100
                elif i < 22:
                    voltages[1] = voltages[1] - 100
                    voltages[2] = voltages[2] - 100
                else:
                    voltages[0] = max(voltages[0] - 100, 0)
                    voltages[1] = max(voltages[1] - 100, 0)
                    voltages[2] = max(voltages[2] - 100, 0)

                for i in range(len(voltages)):
                    self.control_voltages[i] = calculate_input_voltage(self.channels[i], voltages[i]/500, use_amp = False)
                    print(f"Sending control signal {self.control_voltages[i]:.2f} to channel {self.channels[i]} for achieving voltage {voltages[i]}")
                    
                print('\n')
                self.set_voltages()

