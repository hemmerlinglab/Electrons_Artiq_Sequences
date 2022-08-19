import numpy as np

import matplotlib.pyplot as plt



x_arr = np.genfromtxt('spec_data_x_2.csv')
y_arr = np.genfromtxt('spec_data_y_2.csv')

plt.figure()

y_arr[y_arr<-30] = np.nan

plt.plot(x_arr/1e9, y_arr)

plt.xlabel('Frequency (GHz)')
plt.ylabel('Transmission Signal (dBm)')

plt.show()



