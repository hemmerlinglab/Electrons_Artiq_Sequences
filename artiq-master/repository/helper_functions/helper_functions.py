import numpy as np
from amp_zotino_params import fit_parameters, old_coeffs

####################################################################
################  Functions for DC Voltage Control  ################
####################################################################

def calculate_input_voltage(chan, volt, use_amp = True):

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

def adjust_control_voltages(target, use_amp = True):

    channels, voltages = target

    input_vector = np.zeros(len(channels))
    for i in range(len(channels)):
        input_vector[i] = calculate_input_voltage(channels[i], voltages[i], use_amp)

    return (channels, input_vector)
    
    
###########################################################################################

S = np.loadtxt("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions/Table/Sampler.csv", delimiter=",")
H = np.loadtxt("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions/Table/HighV.csv", delimiter=",")

def calculate_Vsampler(chan, V):
    """convert sampler read value into the voltage sent into the sampler."""
    k = S[chan][0]
    b = S[chan][1]
    Vsampler = (V-b)/k
    return Vsampler

def calculate_HighV(chan, V):
    """convert control voltage (Zotino ACTUAL output) to high voltage."""
    k = H[chan][0]
    b = H[chan][1]
    Vhigh = k*V+b
    return Vhigh 

def calculate_Vin(chan, Vt):
    """convert high voltage to control signal sent to Zotino"""
    k1 = H[chan][0]
    b1 = H[chan][1]
    V0 = (Vt-b1)/k1

    Vin = calculate_input_voltage(chan, V0, use_amp = False)
    return Vin

def safe_check(V, mode = "act_voltages"):
    """Return True if unsafe"""
    if mode == "act_voltages":
        return abs(V[1]-V[0])>2005 or V[2]+5 < V[1]

    elif mode == "setpoint":
        return abs(V[1]-V[0])>2000 or V[2]< V[1]

####################################################################
######  Functions for compensation field Bayesian Optimizer  #######
####################################################################

def latin_hypercube(n_samples, bounds, seed=None):
    """
    Latin Hypercube Sampling
    ------------------------------
    1) Parameters
       n_samples (int): number of points to sample
       bounds (d x 2 list): range to sample, d is number of dimensions
       seed (int or None): for reproducing the same result
    ------------------------------
    2) Returns
       samples (n_samples x d numpy.ndarray): sampled points
    """

    # Create a random number generator (RNG)
    rng = np.random.default_rng(seed)

    # Initialization
    bounds = np.array(bounds, dtype=float)
    dim = bounds.shape[0]
    samples = np.zeros((n_samples, dim))

    cut = np.linspace(0, 1, n_samples + 1)

    for j in range(dim):

        # Get n_sample random points in each dimension in the range of [0, 1]
        u = rng.random(n_samples)
        points_1d = cut[:-1] + u * (cut[1:] - cut[:-1])

        # Shuffle points in each dimension
        rng.shuffle(points_1d)

        # Map [-1, 1] to the actual range
        low, high = bounds[j]
        samples[:, j] = low + points_1d * (high - low)

    return samples

