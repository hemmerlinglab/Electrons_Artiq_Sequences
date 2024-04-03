import socket
import time
import numpy as np

class RS:
    
    def __init__(self):

        TCP_IP = '192.168.42.61'
        TCP_PORT = 5025

        self.command_delay = 0.1

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        s.connect((TCP_IP,TCP_PORT))
    
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

    def close(self):

        self.socket.close()


  
