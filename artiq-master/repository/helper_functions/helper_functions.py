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

        # Map [0, 1] to the actual range
        low, high = bounds[j]
        samples[:, j] = low + points_1d * (high - low)

    return samples

def gaussian_similarity(X1, X2, length_scale = 0.3, variance = 1.0):
    """
    Calculate gaussian similarity matrix of two sets of points
    ----------------------------------------------------------------
    0) Theory
       Calculate the similarities of two sets of points by Gaussian function
       Similarity K_ij = exp(-distance_ij**2/(2*length_scale**2))
       Where distance_ij is Euclidean distance between the i-th point in set
       1 and the j-th point in set 2.
       The function will return all K_ij values in the form of a matrix
    ----------------------------------------------------------------
    1) Parameters
       X1: set 1 of points [n_sample x n_dimension]
       X2: set 2 of points [n_sample x n_dimension]
       length_scale: determines how strict the standard of similar would be
       variance: the similarity value should match the scale of y variance for
                 good optimization, so you need to enter delta y scale here
    ----------------------------------------------------------------
    2) Returns
       K: similarity matrix between samples X1 and X2
    """

    # Make sure input X1 and X2 are at least 2D arrays
    X1 = np.atleast_2d(X1).astype(float)
    X2 = np.atleast_2d(X2).astype(float)

    # Compute Euclidean distance ||x-x'||**2 for the sample
    diff = X1[:, None, :] - X2[None, :, :]
    D = np.sum(diff * diff, axis=2)

    # Compute similarity matrix and return
    return variance * np.exp(-0.5 * D / (length_scale ** 2 + 1e-16))

def normalize_coordinates(X, bounds):
    """
    Rescale bounds to [0, 1] in every dimension
    """

    # To support ArrayLike objects, e.g. Python List
    X = np.asarray(X, dtype=float)
    bounds = np.asarray(bounds, dtype=float)

    # Calculation
    lower = bounds[:, 0]
    upper = bounds[:, 1]
    width = upper - lower
    return (X - lower) / width

def normalize_values(ys):
    """
    Rescale y data to make variance(y) ~= 1
    """

    # To support ArrayLike objects, e.g. Python List
    ys = np.asarray(ys, dtype=float)

    y_mean = np.mean(ys)
    y_std = np.std(ys)
    return (ys - y_mean) / y_std

def gaussian_process_predictor(X_train, y_train, X_test,
                               noise        = 1e-3,
                               length_scale = 0.3,
                               variance     = 1.0):
    """
    Predict function values and their uncertainties
    -----------------------------------------------------
    0) Theory
    Prediction is done by Gaussian Process. The predictor predict values
    and uncertainties at X_test based on data from X_train and y_train.
    X_train and X_test are assumed already normalized in to [0, 1], y_train
    is assumed already normalized to mu = 0, sigma = 1.
    predicted function f* obey normal distribution f* ~ N(mu, sigma), where:
    mu       = Ks.T * (K + noise**2 * I).inv * y
    Sigma**2 = Kss - Ks.T * (K + noise**2 * I).inv * Ks
    In which K is Gaussian similarity matrix between X_train and X_train, Ks
    is Gaussian similarity matrix between X_train and X_test, y is y_train.
    Here we only use diagonal of Kss, because we return only uncertainties of
    the predicted values, not correlations.
    -----------------------------------------------------
    1) Parameters
       X_train: [n_sample x n_dimension], array-like, x data for the GP
                predictor to reference to
       y_train: [n_sample], array-like, y data for the GP predictor to
                reference to
       X_test:  [n_point x n_dimension], array-like, positions you ask the
                GP predictor to predict
       noise:   float or array-like, anticipated noise level on y for the
                same point at uniform level or point-wise level
       length_scale: determines how strict the standard of similar would be
       variance: anticipated difference on y for different points
    -----------------------------------------------------
    2) Returns
       mu:    predicted values for positions in X_test
       sigma: predicted uncertainties for positions in X_test
    """

    # Calculate similarity matrix of training points
    K = gaussian_similarity(X_train, X_train,
                            length_scale=length_scale, variance=variance)

    # Add observation noise on the diagonal
    noise = np.asarray(noise, dtype=float)
    K[np.diag_indices_from(K)] += noise ** 2

    # Calculate similarity matrix between training and target points
    Ks = gaussian_similarity(X_train, X_test,
                             length_scale=length_scale, variance=variance)
    
    # Solve for prediction
    # --------------------------------------------------------
    # 1) Use Cholesky factorization to achieve fast and reliable inversion
    L = np.linalg.cholesky(K)
    
    # 2) Solve for (K + noise**2 * I).inv * y using the result of Cholesky
    alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))

    # 3) Solve for (K + noise**2 * I).inv * Ks using the result of Cholesky
    v = np.linalg.solve(L, Ks)
    
    # 4) Calculate averages and uncertainties
    mu = Ks.T @ alpha
    Kss_diag = np.diag(gaussian_similarity(X_test, X_test,
                                           length_scale=length_scale,
                                           variance=variance))
    var = np.maximum(Kss_diag - np.sum(v * v, axis=0), 0.0)

    return mu, np.sqrt(var)

def expected_improvement(mu, sigma, y_best, xi=0.01):
    """
    Expected Improvment for Bayesian Optimization
    ---------------------------------------------------
    0) Theory
    This function takes the result mu and sigma calculated by the 
    gaussian_process_predictor function and calculate their expected
    improvement. The expected improvement is defined by:
    I(x) = max(f(x) - y_best - xi, 0)
    Where xi is a small offset to encourage exploration.
    Expected improvement I(x) is a random variable that satisfy normal
    distribution, whose expectation is given by:
    EI(x) = (mu - y_best - xi) * Phi(Z) + sigma * phi(Z)
    Where Z = (mu - y_best - xi) / sigma, Phi and phi are CDF and PDF
    of normal distribution.
    EI at where sigma ~ 0 is set to 0 to discourage resampling near the
    points we already sampled.
    ---------------------------------------------------
    1) Parameters
       mu:     predicted value calculated by gaussian_process_predictor
       sigma:  uncertainty value calculated by gaussian_process_predictor
       y_best: float, best observed objective value so far
       xi:     float, offset to encourage exploration
    ---------------------------------------------------------
    2) Returns
       ei: Expected improvement at each proposed point
    """

    # Constants
    SQRT2PI = 2.50662827463
    SQRT2 = 1.41421356237
    THRESHOLD = 1e-12

    # Avoid division by zero
    sigma_safe = np.where(sigma <= THRESHOLD, THRESHOLD, sigma)

    # Helper functions
    # ----------------------
    # 1) Normal distribution - Density Function
    def _phi(z):
        return np.exp(-0.5 * z * z) / SQRT2PI
    # 2) Normal distribution - Cumulative Function
    def _Phi(z):
        return 0.5 * (1.0 + np.erf(z / SQRT2))
    
    # Calculate expected improvement
    improvement = mu - y_best - xi
    Z = improvement / sigma_safe
    ei = improvement * _Phi(Z) + sigma * _phi(Z)
    ei = np.where(sigma < THRESHOLD, 0.0, ei)

    return ei

def gaussian_process_hyperparameters(X_train, y_train):
    """
    Choose GP kernel scales and noise level from data
    -------------------------------------------------
    0) Physics mindset
       The routine tunes the Gaussian Process so that the kernel width and
       noise match the spread of the measured signals. It scans a small grid
       of length scales and relative noise levels, then keeps the settings
       that maximize the log-marginal likelihood of the observations.
    -------------------------------------------------
    1) Parameters
       X_train: [n_sample x n_dimension], normalized coordinates of sampled
                points
       y_train: [n_sample], normalized measurements collected at X_train
    -------------------------------------------------
    2) Returns
       best_length_scale: kernel width giving the highest likelihood
       variance:          overall variance of y_train (used as kernel scale)
       noise:             per-point noise estimate combining absolute and
                          relative terms
       xi:                exploration offset for expected improvement
    """

    # Evaluate variance
    variance = np.var(y_train)
    
    # Evaluate noise
    sigma_y = np.sqrt(variance)
    abs_noise = 0.02 * sigma_y
    rel_noise_levels = [0.02, 0.03, 0.05]

    # Evaluate length_scale
    length_scale_levels = [0.1, 0.2, 0.3, 0.4]

    best_lml = -np.inf
    best_rel_noise = rel_noise_levels[0]
    best_length_scale = length_scale_levels[0]

    for ell in length_scale_levels:
        K = gaussian_similarity(X_train, X_train, length_scale=ell, variance=variance)

        for rel_noise in rel_noise_levels:
            K_ = K.copy()
            K_[np.diag_indices_from(K_)] += abs_noise**2 + (rel_noise * y_train)**2

            L = np.linalg.cholesky(K_)
            alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_train))

            log_det = 2.0 * np.sum(np.log(np.diag(L)))
            quad = y_train @ alpha

            # log-marginal likelihood
            lml = -0.5 * quad - 0.5 * log_det

            if lml > best_lml:
                best_lml = lml
                best_length_scale = ell
                best_rel_noise = rel_noise

    # for normalized y, a fixed xi is fine
    xi = 0.01

    # Final noise
    noise = np.sqrt(abs_noise**2 + (best_rel_noise * y_train)**2)

    return best_length_scale, variance, noise, xi

def bo_suggest_next(X_observed, y_observed, bounds,
                    n_candidates = 256,
                    auto_mode    = True,
                    length_scale = 0.3,
                    variance     = 1.0,
                    noise        = 1e-2,
                    xi           = 0.01,
                    seed         = None):
    """
    Propose the next field setpoint from current BO state
    -----------------------------------------------------
    0) Physics mindset
       Given past measurements of the objective versus electric-field
       components, the function trains a Gaussian Process surrogate and
       evaluates the expected improvement (EI) on a fresh Latin Hypercube
       batch. The candidate with the largest EI is chosen as the next point
       to test in the experiment.
    -----------------------------------------------------
    1) Parameters
       X_observed:   [n_sample x n_dimension], measured field settings
       y_observed:   [n_sample], measured objective values at X_observed
       bounds:       [n_dimension x 2], limits for each field component
       n_candidates: int, number of trial points drawn for EI evaluation
       auto_mode:    bool, fit kernel hyperparameters from data when True
       length_scale: float, kernel width used when auto_mode is False
       variance:     float, kernel amplitude used when auto_mode is False
       noise:        float or array-like, assumed noise on measurements when
                     auto_mode is False
       xi:           float, exploration offset for EI when auto_mode is False
       seed:         int or None, RNG seed for reproducible candidate draws
    -----------------------------------------------------
    2) Returns
       candidates[idx]: suggested next point in the original coordinate scale
       ei[idx]:         expected improvement associated with the suggestion
    """

    # Normalize X and y scale for better numerical stability
    X_normalized = normalize_coordinates(X_observed, bounds)
    y_normalized = normalize_values(y_observed)

    # Draw a batch of candidates in the domain
    candidates = latin_hypercube(n_candidates, bounds, seed=seed)
    candidates_normalized = normalize_coordinates(candidates, bounds)

    # Learn hyperparameters from observation data if auto mode was on
    if auto_mode:
        length_scale, variance, noise, xi = gaussian_process_hyperparameters(X_normalized, y_normalized)

    # Fit GP on current observation data
    mu, sigma = gaussian_process_predictor(X_normalized, y_normalized,
                                           candidates_normalized,
                                           noise=noise,
                                           length_scale=length_scale,
                                           variance=variance)

    # Calculated expected improvements for candidates
    y_best_normalized = np.max(y_normalized)
    ei = expected_improvement(mu, sigma, y_best_normalized, xi=xi)

    # Suggest the next point and its expected improvement
    idx = np.argmax(ei)
    return candidates[idx], ei[idx]
