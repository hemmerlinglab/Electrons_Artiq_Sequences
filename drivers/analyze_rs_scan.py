# Script to regenerate plots of rs_scan.py
import numpy as np
import matplotlib.pyplot as plt

path = "/home/electrons/software/Electrons_Artiq_Sequences/drivers/data/"
date = "20250627"
experiment_name = "ucb_T"
basefilename = path + date + '/' + experiment_name

freq = np.genfromtxt(basefilename + "_x.csv")
level = np.genfromtxt(basefilename + "_y.csv")

plt.figure(figsize=(12,8))
plt.plot(freq, level)
plt.title(experiment_name)
plt.xlim((1.0e9, 2.0e9))
plt.xlabel("Frequency")
plt.ylabel("Level")
plt.savefig(basefilename + ".png")
plt.show()
