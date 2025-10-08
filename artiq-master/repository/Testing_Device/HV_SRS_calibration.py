from artiq.experiment import *
import numpy as np
import time
import datetime

import sys
import os
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import calculate_input_voltage

save_directory = "/home/electrons/software/Electrons_Artiq_Sequences/drivers/data/"

class HVSupplyCalibration(EnvExperiment):

    def build(self):

        self.setattr_device("core")
        self.setattr_device("zotino0")
        self.setattr_device("sampler0")

    @kernel
    def zotino_out(self, channel, level):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(channel, 65000)
        self.zotino0.write_dac(channel, level)
        self.zotino0.load()

        return

    @kernel
    def sampler_read(self):

        self.core.break_realtime()
        self.sampler0.init()
        delay(200*us)

        readings = [0.0] * 8
        self.sampler0.sample(readings)
        self.set_dataset("sampler_voltages", readings, broadcast=True)

    def prepare(self):

        self.test_voltages = np.linspace(0, 6.0, 61)

        self.adjusted_voltages = []
        for v in self.test_voltages:
            v28 = calculate_input_voltage(28, v)
            v29 = calculate_input_voltage(29, v)
            v30 = calculate_input_voltage(30, v)
            self.adjusted_voltages.append([v28, v29, v30])

        self.measured_voltages = []

        print("Calibration Start ==================================")

    def analyze(self):

        print("Calibration Done ===================================")

        current_datetime = datetime.datetime.today()
        today = current_datetime.strftime("%Y%m%d")
        os.makedirs(os.path.join(save_directory, today), exist_ok=True)

        now = current_datetime.strftime("%Y%m%d_%H%M%S")
        basefilename = os.path.join(save_directory, today, now)

        setpoints = np.array(self.test_voltages)
        adjusted = np.array(self.adjusted_voltages)
        measured = np.array(self.measured_voltages)

        print("Saving Data ...")

        np.savez(
            basefilename + "_HVCalibration.npz",
            setpoints = setpoints,
            adjusted = adjusted,
            measured = measured
        )
        np.savetxt(basefilename + "_setpoints.csv", setpoints)
        np.savetxt(basefilename + "_adjusted.csv", adjusted)
        np.savetxt(basefilename + "_measured.csv", measured)

        print(f"Calibration Data saved to {basefilename}")

    def run(self):

        self.core.reset()

        total = len(self.adjusted_voltages)
        for i, vs in enumerate(self.adjusted_voltages):
            print(f"\nTesting setpoints {i+1}/{total}: {self.test_voltages[i]:.1f}\n"
                  f"  - DAC[28,29,30] = ({vs[0]:.4f},{vs[1]:.4f},{vs[2]:.4f})")

            self.zotino_out(28, vs[0])
            self.zotino_out(29, vs[1])
            self.zotino_out(30, vs[2])
            
            time.sleep(10.0)

            self.sampler_read()
            read = self.get_dataset("sampler_voltages")
            self.measured_voltages.append(read)
            print(f"  - measured[28,29,30] = ({read[0]:.4f},{read[1]:.4f},{read[2]:.4f})")

