'''Zijue Luo: Trying to write a code to scan the 390 spectrum'''
from artiq.experiment import *
import numpy as np
import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *


class Sample_and_Hold_Lock(EnvExperiment):

    def build(self):

        self.setattr_device('core')

        # Parameters
        self.setattr_argument('frequency_422', NumberValue(default=709.077801,unit='THz',scale=1,ndecimals=6,step=1e-6))

    def send_setpoint(self, frequency):

        # Initialize the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = ('192.168.42.136', 63700)
        
        # Send the setpoint
        print('Sending new setpoint: ', frequency)
        sock.connect(server_address)
        msg = '{0:.9f}'.format(frequency)
        try:
            sock.sendall(msg.encode())

        finally:
            sock.close()

    def run(self):

        print(self.frequency_422)
