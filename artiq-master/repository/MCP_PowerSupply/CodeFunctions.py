from amp_zotino_params import fit_parameters, old_coeffs            

def calculate_input_voltage(chan, volt, use_amp = False):

    if use_amp: key = 'Input→Amp'                        
    else: key = 'Input→Artiq'                            

    try:                                                 
        k = fit_parameters[chan + 1][key]['k']           
        b = fit_parameters[chan + 1][key]['b']
        input_voltage = (volt - b) / k 
    except KeyError:                                     
        k, b = old_coeffs[chan]         
        input_voltage = k * volt + b

    return input_voltage


# Vsampler, Vhigh coefficient

# import pandas as pd 
# S = pd.read_csv("Table/Sampler.csv", header=None)
# H = pd.read_csv("Table/HighV.csv", header=None)
# 實驗室電腦讀取不到pandas，只能用：

import numpy as np

S = np.loadtxt("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/MCP_PowerSupply/Table/Sampler.csv", delimiter=",")
H = np.loadtxt("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/MCP_PowerSupply/Table/HighV.csv", delimiter=",")


# 讀取出的Vsampler比實際Vout小
def calculate_Vsampler(chan, V):
    k = S[chan][0]
    b = S[chan][1]
    Vsampler = k*V+b
    return Vsampler

def calculate_HighV(chan, V):
    k = H[chan][0]
    b = H[chan][1]
    Vhigh = k*V+b
    return Vhigh 

def calculate_Vin(chan, Vt):
    k1 = H[chan][0]
    b1 = H[chan][1]
    V0 = (Vt-b1)/k1

    Vin = calculate_input_voltage(chan, V0, use_amp = False)
    return Vin
