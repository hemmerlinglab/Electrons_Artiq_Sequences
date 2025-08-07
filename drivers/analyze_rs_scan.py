# Script to regenerate plots of rs_scan.py
import numpy as np
import matplotlib.pyplot as plt

path = "/home/electrons/software/Electrons_Artiq_Sequences/drivers/data/"
date = "20250807_ripple_research"
experiment_name = "TrapOut_Atten20dB_In-2dBm"
basefilename = path + date + '/' + experiment_name

freq = np.genfromtxt(basefilename + "_x.csv")
level = np.genfromtxt(basefilename + "_y.csv")

plt.figure(figsize=(12,8))
plt.plot(freq, level)
plt.title(experiment_name)
plt.xlim((1.2e9, 2.4e9))
plt.xlabel("Frequency")
plt.ylabel("Level")
plt.savefig(basefilename + ".png")
plt.show()
