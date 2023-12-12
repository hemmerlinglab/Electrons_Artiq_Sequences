import numpy as np

x = np.array([1, 2, 3, 4, 5])
y = x ** 2

f = open('test.csv', 'w')
for i in range(len(x)):
	f.write(str(x[i]) + ', ' + str(y[i]) + '\n')
f.close()
