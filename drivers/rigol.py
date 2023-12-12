import numpy as np
import time
from base_instruments import base_visa_instrument


# Rigol Function Generator

class Rigol_DSG821(base_visa_instrument):

    # electron rigol IP: .65
    # molecules rigol IP: .46

    def __init__(self, IP = '192.168.42.65'):

        # call constructor of parent class
        super().__init__(IP)

        return

    def set_freq(self, freq):

        self.write(':FREQ {0}MHz'.format(float(freq)))
        
        #time.sleep(1)

        return

    def set_level(self, level):

        self.write(':LEV {0}'.format(float(level)))

        return

    def on(self):

        self.write(':OUTP ON')

        return

    def off(self):

        self.write(':OUTP OFF')

        return




##################################################################################################
# Main
##################################################################################################

if __name__ == "__main__":

    import matplotlib.pyplot as plt

    fg = Rigol_DSG821()

    fg.id()

    fg.set_freq(8.0)
    fg.set_level(0.0)

    fg.close()


