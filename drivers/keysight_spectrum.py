import socket
import time
import numpy as np

class Keysight:
    
    def __init__(self):

        TCP_IP = '192.168.42.63'
        TCP_PORT = 5025

        self.command_delay = 0.01

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        s.connect((TCP_IP,TCP_PORT))
    
        s.send(b"*IDN?\n")
        t = s.recv(1024)
    
        print(t)
        
        self.socket = s
    

    def send(self, msg):

        send_msg = msg + '\n'

        self.socket.send(send_msg.encode())

        time.sleep(self.command_delay)

    def recv(self):

        self.msg = self.socket.recv(1024)

        return self.msg

    def query(self, msg):

        self.send(msg)

        self.msg = self.socket.recv(1024)

        self.msg = self.msg.decode().strip('\n')

        return self.msg


    def set_center_freq(self, freq):

        self.send(':FREQ:CENT ' + str(freq) + ' Hz')

    def set_span(self, span):

        self.send(':FREQ:SPAN ' + str(span) + ' Hz')

    def marker_on(self, no):

        self.send(':CALC:MARK' + str(no) + ':STATE ON')

    def marker_measure(self, no, wait_time = None):

        self.send(':CALC:MARK' + str(no) + ':MAX')

        if not wait_time is None:
            time.sleep(wait_time)

        x = self.query(':CALC:MARK' + str(no) + ':X?')
        
        y = self.query(':CALC:MARK' + str(no) + ':Y?')        
        
        err = self.query(':SYST:ERR?')        

        return (np.float64(x), np.float64(y), err)

    def close(self):

        self.socket.close()

   
