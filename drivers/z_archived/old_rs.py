import socket
import time
import numpy as np

def init_RS():

    TCP_IP = '192.168.42.149'
    TCP_PORT = 5025


    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    s.connect((TCP_IP,TCP_PORT))
    
    s.send(b"*IDN?\n")
    t = s.recv(24)
    
    print(t)
    
    return s



#    s.send(b"OUTP OFF\n")
#    
#    time.sleep(1)
#    
#    s.send(b"FREQ 1.72345 MHz\n")
#    
#    time.sleep(1)
#    
#    #s.send(b"SOUR:POW:LEV:IMM:AMPL 2\n")
#    
#    s.send(b":POW -2\n")
#    
#    
#    s.send(b"OUTP ON\n")
#    
#    time.sleep(1)
#    
#    s.send(b"OUTP OFF\n")
#    
    
    #s.send(b'SYST:REB') # reboot generator


rs = init_RS()

rs.send(b"FREQ 1.8234 GHz\n")
time.sleep(1)

rs.send(b":POW -3\n")
time.sleep(1)

rs.send(b"OUTP ON\n")
time.sleep(1)


TCP_IP = '192.168.42.63'
TCP_PORT = 5025


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect((TCP_IP,TCP_PORT))

s.send(b"*IDN?\n")
t = s.recv(1024)

print(t)

#start_freq = 0.5
#stop_freq 7.001
#step = 0.001

#cent_freq = [np.arange(start_freq, stop_freq, step)]
#for freq in cent_freq:
    #s.send(b":FREQ:CENT {:.3f} GHz\n".format(str(freq)))

print()
print()


s.send(b":CALC:MARK1:STATE ON\n")

s.send(b":CALC:MARK1:STATE?\n")
err2 = s.recv(1024)
print(err2)


s.send(b":FREQ:CENT 1.567 GHz\n")
s.send(b":FREQ:CENT?\n")
result = s.recv(1024)
print(result)



s.send(b":FREQ:SPAN 820 MHz\n")
s.send(b":FREQ:SPAN?\n")
result = s.recv(1024)
print(result)


#s.send(b":MEAS:SAN2?")

s.send(b":CALC:MARK1:MAX\n")

s.send(b":CALC:MARK1:X?\n")

x = s.recv(1024)

s.send(b":CALC:MARK1:Y?\n")
y = s.recv(1024)

s.send(b":SYST:ERR?\n")
err = s.recv(1024)


print("POS: {0} HEIGHT: {1}, ERR: {2}".format(x,y,err))





rs.send(b"OUTP OFF\n")



