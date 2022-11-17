from artiq.experiment import *
import numpy as np

import socket
import time
import sys
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *



class Lock_test(EnvExperiment):
    
    def build(self):
        
        self.config_dict = []
        self.wavemeter_frequencies = []
        
        self.setattr_device('core')

        # Setting the lock frequency for 422 and the scan range for 390
        self.my_setattr('frequency_422', NumberValue(default=709.078540,unit='THz',scale=1,ndecimals=6,step=1e-6))
        self.my_setattr('frequency_390', NumberValue(default=766.056,unit='THz',scale=1,ndecimals=6,step=1e-6))


    def my_setattr(self, arg, val):
        
        # define the attribute
        self.setattr_argument(arg,val)

        # add each attribute to the config dictionary
        if hasattr(val, 'unit'):
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'unit' : '" + str(val.unit) + "'})")
        else:
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + "})")


    def set_single_laser(self, which_laser, frequency, do_switch = False, wait_time = None):
        
        if which_laser == 422:
            channel = 5
        elif which_laser == 390:
            channel = 6                

        if do_switch:
            switch = 1
        else:
            switch = 0

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('192.168.42.136', 63700)

        print('Sending new setpoint: ' + str(frequency))
        sock.connect(server_address)
        
        message = "{0:1d},{1:.9f},{2:1d},{3:3d}".format(int(channel), float(frequency), int(switch), int(wait_time))
    
        sock.sendall(message.encode())
        
        sock.close()

        time.sleep(2*wait_time/1000.0)
       
        return



    def run(self):
       
        self.set_single_laser(422, self.frequency_422, do_switch = True, wait_time = 1000)
        self.set_single_laser(390, self.frequency_390, do_switch = True, wait_time = 1000)

        time.sleep(3)




