import numpy as np
from traps import traps
import sys

class Electrodes(object):

    def __init__(self, trap = "UCB 3 PCB", flipped = False):

        if flipped: trap = trap + " Flipped"

        self.elec_dict = traps[trap]["elec_zotino_chs"]
        self.multipoles = traps[trap]["multipoles_order"]
        self.elec_list = traps[trap]["electrodes_order"]
        self.read_in_cfile(traps[trap]["cfile"])

        return


    def read_in_cfile(self, filename):
        
        Cfile_text = open(filename).read().split('\n')[:-1]
        
        head = []
        body = []
        for i in range(len(Cfile_text)):
          if Cfile_text[i].find(':') >= 0: head.append(Cfile_text[i])
          else: body.append(Cfile_text[i].split())

        num_columns = 1 # this needs to change if the cfile has more than one column

        self.multipole_matrix = {
            elec: {
                mult: 
                        [
                            float(body[eindex + mindex*len(self.elec_dict)][i]) for i in range(num_columns)
                        ] for mindex, mult in enumerate(self.multipoles)
                } for eindex, elec in enumerate(self.elec_list)
            }

        return


    def getVoltageMatrix(self, multipole_vector):
        
        # example of multipole vector:
        #
        # multipole_vector = {
        #        'Ex' : 0,
        #        'Ey' : 0,
        #        'Ez' : 0,
        #        'U1' : 0,
        #        'U2' : -1,
        #        'U3' : 0,
        #        'U4' : 0,
        #        'U5' : 0
        #    }

        num_columns = 1
            
        voltage_matrix = {}
        for e in self.elec_dict.keys():
            voltage_matrix[e] = [0. for n in range(num_columns)]
            for n in range(num_columns):
                for m in self.multipoles:
                    voltage_matrix[e][n] += self.multipole_matrix[e][m][n] * multipole_vector[m]

        channel_list = []
        voltage_list = []
        for k in voltage_matrix.keys():

            channel_list.append(self.elec_dict[k])
            voltage_list.append(voltage_matrix[k][0])
        
        return (np.array(channel_list, dtype = int), np.array(voltage_list, dtype = float))


    def print_voltage_matrix(self, multipole_vector):
        
        inds, vols = self.getVoltageMatrix(multipole_vector)

        for i in range(len(inds)):
            print(f"ch{inds[i]}:\t{vols[i]:6.2f}V")
        print()

        return




class Flipped_Electrodes(object):


    def __init__(self):

        # connects the Zotino channel number with the electrodes
        self.elec_dict = {
            'tg' : 100,
            'tl1' : 12,
            'tl2' : 13,
            'tl3' : 14,
            'tl4' : 15,
            'tl5' : 16,
            'tr1' : 21,
            'tr2' : 20,
            'tr3' : 19,
            'tr4' : 18,
            'tr5' : 17,
            'bl1' : 0,
            'bl2' : 1,
            'bl3' : 2,
            'bl4' : 3,
            'bl5' : 4,
            'br1' : 9,
            'br2' : 8,
            'br3' : 7,
            'br4' : 6,
            'br5' : 5,
         }
        # needle top: channel 10
        # needle bottom: channel 22
        # GND top: channel 11
        # GND bottom: channel 23
        # GND bottom: channel 24

        
        self.multipoles = ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5']
        self.read_in_cfile('/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions/Cfile.txt')


        return

    def read_in_cfile(self, filename):
        
        Cfile_text = open(filename).read().split('\n')[:-1]
        
        head = []
        body = []
        for i in range(len(Cfile_text)):
          if Cfile_text[i].find(':') >= 0: head.append(Cfile_text[i])
          else: body.append(Cfile_text[i].split())


        num_columns = 1 # this needs to change if the cfile has more than one column

        self.multipole_matrix = {
            elec: {
                mult: 
                        [
                            float(body[eindex + mindex*len(self.elec_dict)][i]) for i in range(num_columns)
                        ] for mindex, mult in enumerate(self.multipoles)
                } for eindex, elec in enumerate(sorted(self.elec_dict.keys()))
            }


        return


    def getVoltageMatrix(self, multipole_vector):
        
        # example of multipole vector:
        #
        # multipole_vector = {
        #        'Ex' : 0,
        #        'Ey' : 0,
        #        'Ez' : 0,
        #        'U1' : 0,
        #        'U2' : -1,
        #        'U3' : 0,
        #        'U4' : 0,
        #        'U5' : 0
        #    }


        num_columns = 1
            
        voltage_matrix = {}
        for e in self.elec_dict.keys():
            voltage_matrix[e] = [0. for n in range(num_columns)]
            for n in range(num_columns):
                for m in self.multipoles:
                    voltage_matrix[e][n] += self.multipole_matrix[e][m][n] * multipole_vector[m]

        channel_list = []
        voltage_list = []
        for k in voltage_matrix.keys():

            channel_list.append(self.elec_dict[k])
            voltage_list.append(voltage_matrix[k][0])
        
        return (np.array(channel_list, dtype = int), np.array(voltage_list, dtype = float))


    def print_voltage_matrix(self, multipole_vector):
        
        v = self.populateVoltageMatrix(multipole_vector)
        
        for l in ['t','b']:
            for k in range(5):
        
                    my_key = l+'l'+str(5-k)
                    my_key2 = l+'r'+str(5-k)
        
                    print("{0:3s} : {1:6.2f}     {2:3s} : {3:6.2f}".format(my_key, v[my_key][0], my_key2, v[my_key2][0]))
        
            print()

        return
