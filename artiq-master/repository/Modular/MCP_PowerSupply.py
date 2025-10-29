# Common Import

import matplotlib.pyplot as plt
import time
import sys

from artiq.experiment import *

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import calculate_Vsampler, calculate_HighV, calculate_Vin, safe_check



# 實驗代碼

class MCP_PowerSupply(EnvExperiment):
    
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0')
        self.setattr_device('sampler0')
        self.setattr_device('scheduler')
        self.setattr_argument('mode', EnumerationValue(['on', 'off', 'custom'],default='custom'))
        self.setattr_argument('front', NumberValue(default=0,unit='V',scale=1,ndecimals=0,step=1))
        self.setattr_argument('back', NumberValue(default=0,unit='V',scale=1,ndecimals=0,step=1))
        self.setattr_argument('anode', NumberValue(default=0,unit='V',scale=1,ndecimals=0,step=1))
        
    def prepare(self):
        self.channels = [28, 29, 30]

        self.SamplerChannels = [0, 1, 2]
        self.NumSamples = len(self.SamplerChannels)
        self.V0 = [0.0] * self.NumSamples
        self.SampleResults=[0.0]*8
        

    @kernel
    def read(self):
        self.core.reset()
        self.core.break_realtime()
        self.sampler0.init()
        delay(200*us)
        
        readings = [0.0]*8
        self.sampler0.sample(readings)
        self.set_dataset("sampler_voltages", readings, broadcast=True)
        self.core.break_realtime()
        

    def process(self):
        self.read()
        self.SampleResults = self.get_dataset("sampler_voltages")[0:3]
        for i in range(len(self.V0)):
            self.V0[i] = calculate_Vsampler(i, self.SampleResults[i])
        return self.V0


    def Vt(self):
        self.process()
        self.Vt = [0.0]*3
        for i in range(len(self.V0)):
            self.Vt[i] = calculate_HighV(i, self.V0[i])
        return self.Vt

    
    def run(self):

        self.Vt()
        if self.mode == 'custom':
            self.Vtarget = [self.front,self.back,self.anode]
        elif self.mode == 'on':
            self.Vtarget = [200, 2200, 2400]
        elif self.mode == 'off':
            self.Vtarget = [0, 0, 0]
        
        if safe_check(self.Vtarget, mode="setpoint"):
            raise ValueError("Unsafe setpoint!")

        if safe_check(self.Vt):
            raise RuntimeError("Initial state is already unsafe!")

        first_cycle = True

        while self.Vt != self.Vtarget:
            self.scheduler.pause()
            sleep_time = 10
            for i in range(len(self.Vt)):
                if abs(self.Vtarget[i]-self.Vt[i]) < 100:
                    self.Vt[i] = self.Vtarget[i]
                    print(self.Vt)
                elif self.Vtarget[i] - self.Vt[i] >= 100:
                    self.Vt[i] += 100
                    print(self.Vt)
                    sleep_time = 20
                elif self.Vtarget[i] - self.Vt[i] <= -100:
                    self.Vt[i] -= 100
                    print(self.Vt)
            # print("zotino_written")
            self.Vin = [0.0]*3
            for i in range(len(self.V0)):
                self.Vin[i] = calculate_Vin(i, self.Vt[i])

            if safe_check(self.Vt):
                raise RuntimeError("Equipment destroyed!")

            if not first_cycle:
                time.sleep(sleep_time)
                #pass

            first_cycle = False

            self.output()
            

    @kernel
    def output(self):
       
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)

        for i in range(len(self.channels)):
            self.zotino0.write_gain_mu(self.channels[i], 65000)
            self.zotino0.load()
            delay(200*us)
            self.zotino0.write_dac(self.channels[i], self.Vin[i])
            self.zotino0.load()
            delay(200*us)

        return

