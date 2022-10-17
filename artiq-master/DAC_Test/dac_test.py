import numpy as np





def populateVoltageMatrix(multipole_vector, elec_dict, multipole_matrix):
        
    num_colums = 1
    #multipole_vector = {m: v for (m,v) in multipole_vector}
        
    voltage_matrix = {}
    for e in elec_dict.keys():
        voltage_matrix[e] = [0. for n in range(num_columns)]
        for n in range(num_columns):
            for m in multipoles:
                voltage_matrix[e][n] += multipole_matrix[e][m][n] * multipole_vector[m]

    return voltage_matrix


elec_dict = {
        'tg' : 0,
        'tl1' : 0,
        'tl2' : 1,
        'tl3' : 2,
        'tl4' : 3,
        'tl5' : 4,
        'tr1' : 0,
        'tr2' : 1,
        'tr3' : 2,
        'tr4' : 3,
        'tr5' : 4,
        'bl1' : 0,
        'bl2' : 1,
        'bl3' : 2,
        'bl4' : 3,
        'bl5' : 4,
        'br1' : 0,
        'br2' : 1,
        'br3' : 2,
        'br4' : 3,
        'br5' : 4,
        }


body = []

Cfile_path = 'Cfile.txt'
Cfile_text = open(Cfile_path).read().split('\n')[:-1]
        
head = []
body = []
for i in range(len(Cfile_text)):
  if Cfile_text[i].find(':') >= 0: head.append(Cfile_text[i])
  else: body.append(Cfile_text[i].split())



multipoles = ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5']

num_columns = 1

multipole_matrix = {
    elec: {
        mult: 
                [
                    float(body[eindex + mindex*len(elec_dict)][i]) for i in range(num_columns)
                ] for mindex, mult in enumerate(multipoles)
        } for eindex, elec in enumerate(sorted(elec_dict.keys()))
    }

m_vec = {
    'Ex' : 0,
    'Ey' : 0,
    'Ez' : 0,
    'U1' : 0,
    'U2' : -1,
    'U3' : 0,
    'U4' : 0,
    'U5' : 0
}


v = populateVoltageMatrix(m_vec, elec_dict, multipole_matrix)

for l in ['t','b']:
    for k in range(5):

            my_key = l+'l'+str(5-k)
            my_key2 = l+'r'+str(5-k)

            print("{0:3s} : {1:6.2f}     {2:3s} : {3:6.2f}".format(my_key, v[my_key][0], my_key2, v[my_key2][0]))

    print()

