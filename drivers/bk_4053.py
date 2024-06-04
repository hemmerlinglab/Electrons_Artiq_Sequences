import socket
import time
import numpy as np

#import matplotlib.pyplot as plt



class BK4053:
    
    def __init__(self):

        TCP_IP = '192.168.42.64'
        #TCP_PORT = 5025
        TCP_PORT = 5024
        #TCP_PORT = 61325

        self.command_delay = 0.1

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        s.connect((TCP_IP,TCP_PORT))
   
        #print('Opened port')

        #s.send(b"*IDN?\n")
        #t = s.recv(1024)
    
        #print(t)
        
        self.socket = s
    
    def send(self, msg):

        send_msg = msg + '\n'

        self.socket.send(send_msg.encode())

        time.sleep(self.command_delay)

    def recv(self):

        self.msg = self.socket.recv(1024)

        return self.msg

    def on(self):

        self.send('OUTP ON')        

    def off(self):

        self.send('OUTP OFF')

    def set_freq(self, freq):

        self.send('FREQ ' + str(freq) + ' Hz')

    def set_ampl(self, ampl):

        self.send(':POW ' + str(ampl))

    def set_carr_delay(self, channel, delay):

        self.send('C' + str(channel) + ':BTWV CARR,DLY,' + str(delay))

        return

    def set_carr_freq(self, channel, frequency):

        self.send('C' + str(channel) + ':BTWV CARR,FRQ,' + str(frequency))

        return
        
    def set_carr_width(self, channel, freq, width):
    
        duty = 100 * width / (1/freq)
        
        self.send('C' + str(channel) + ':BTWV CARR,DUTY,' + str(duty))
        
        return
        
    def set_carr_ampl(self, channel, amplitude):
    
    	self.send('C' + str(channel) + ':BTWV CARR,AMP,' + str(amplitude))
    	
    	return
    	
    def set_carr_offset(self, channel, offset):
    
    	self.send('C' + str(channel) + ':BTWV CARR,OFST,' + str(offset))
    	
    	return

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()


if __name__ == '__main__':

    bk = BK4053()

    bk.close()


