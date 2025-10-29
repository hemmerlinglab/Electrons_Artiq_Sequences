# Common Import

import numpy as np
import matplotlib.pyplot as plt
import time

from artiq.experiment import *

import CodeFunctions




# Reading Samplers

class ReadSampler(EnvExperiment):

    def build(self):
        self.setattr_device('core')
        self.setattr_device('sampler0')

    
    def prepare(self):
        self.SamplerChannels = [0, 1, 2]
        self.NumSamples = len(self.SamplerChannels)
        self.V0 = np.array([0.0] * self.num_samples)
        

    @kernel
    def read(self):
        self.core.reset()
        self.core.break_realtime()
        self.sampler0.init()
        delay(200*us)
        
        self.sample_results = self.sampler0.sample(self.SamplerChannels)
        self.core.break_realtime()
        

    def process(self):
        for i in range(len(self.V0)):
            self.V0[i] = calculate_Vsampler(i, self.sample_results[i])
        return self.V0

    def keep(self):
        shared_data["V0"] = self.process()




# 輸出壓

class Experiment(EnvExperiment):
    
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0')
        
    def prepare(self):
        self.channels = [28, 29, 30]
        self.V0 = shared_data.get("V0", None)


    def Vt(self):
        self.Vt = np.array([0.0]*3)
        for i in range(len(self.V0)):
            self.Vt = calculate_HighV(i, self.V0[i])
        return self.Vt

    
    def run(self):
        self.Vtarget = [200,2000,2000]                      # 在這裡修改你的目標電壓
        
        if np.abs(self.Vtarget[1]-self.Vtarget[0])>2000 or self.Vtarget[2]< self.Vtarget[1]:
            raise ValueError("Invalid Setpoint")

        if np.abs(self.Vt[1]-self.Vt[0])>2000 or self.Vt[2] < self.Vt[1]:
            raise RuntimeError("Initial state is already unsafe!")

        first_cycle = True

        while self.Vt != self.Vtarget:
            sleep_time = 10
            for i in range(len(Vt)):
                if np.abs(self.Vtarget[i]-self.Vt[i])<100:
                    self.Vt[i] = self.Vtarget[i]
                    print(Vt)
                elif self.Vtarget[i] - self.Vt[i] >= 100:
                    self.Vt[i] += 100
                    print(self.Vt)
                    sleep_time = 20
                elif self.Vtarget[i] - self.Vt[i] <= 100:
                    self.Vt[i] -= 100
                    print(self.Vt)
            print("zotino_written")

            if np.abs(self.Vt[1]-self.Vt[0])>2000 or self.Vt[2] < self.Vt[1]:
                raise RuntimeError("Equipment destroyed!")

            if not first_cycle and self.Vt != self.Vtarget:
                time.sleep(sleep_time)

            first_cycle = False
            

    def Vin(self):
        self.Vin = np.array([0.0]*3)
        for i in range(len(self.V0)):
            self.Vin = calculate_input_voltage(i, self.V0[i])
        return self.Vin


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
            self.zotino0.write_dac(self.channels[i], self.control_voltages[i])
            self.zotino0.load()
            delay(200*us)

        return
