from rs import RS
from keysight_spectrum import Keysight

import numpy as np
import time

RF_SYSTEM_PARAMS = {

    # change this when the RF system changes
    "update_date": 20251217,

    # generator range (amplitude, in dBm)
    "amplitude_min": -30.0,
    "amplitude_max": +11.0,

    # generator range (frequency, in Hz)
    "frequency_min": 1e+6,
    "frequency_max": 31.8e+9,

    # spectrum analyzer measurement settings
    "span_hz": 50e+6,
    "div_dB": 1.0,

    # rf system dependent functions
    "careful_functions": [
        "_update_setpoint_fast",
        "_get_initial_setpoint",
        "_set_vertical_window",
        "_convert_frequency_value",
    ]
}

class RFController:

    # 1) Initialization
    # ===============================================================
    def __init__(
        self,
        marker_no: int = 1,
        mode = "setpoint",            # "setpoint", "actual" or "locked"
        amplitude: float = 4.0,
        frequency: float = 1.732e+09
        ):

        # 1. Initialize Devices
        # ---------------------------------------
        self.generator = RS()
        self.spec = Keysight()

        # 2. Store Attributes
        # ---------------------------------------
        self.marker_no = marker_no
        self.amplitude = amplitude

        if mode not in ("setpoint", "actual", "locked"):
            raise ValueError("Controller Mode not Supported!")
        self.mode = mode

        self.frequency = self._convert_frequency_value(frequency)

        # 3. Hidden Attributes (Constants)
        # ---------------------------------------
        self._divA = RF_SYSTEM_PARAMS["div_dB"]
        self._span = RF_SYSTEM_PARAMS["span_hz"]

        # 4. Generator setpoint bounds
        # ---------------------------------------
        self._setpoint_min = RF_SYSTEM_PARAMS["amplitude_min"]
        self._setpoint_max = RF_SYSTEM_PARAMS["amplitude_max"]

        # 5. Last Setpoint for Actual and Locked Mode
        # ---------------------------------------
        self._last_setpoint = None

    # 2) Turn RF on and off
    # ===============================================================
    def on(self):

        # Turn on the RF Generator
        self.generator.on()

        # Initialize amplitude and frequency
        self.set_frequency(self.frequency)
        self.set_amplitude(self.amplitude)

        # Initialize Spec Measurement
        self.spec.set_div_ampl(self._divA)
        self.spec.set_span(self._span)
        self.spec.marker_on(self.marker_no)

    def off(self, kill_sockets = True):

        self.generator.off()
        if kill_sockets:
            self.generator.close()
            self.spec.close()

    # 3) Internal Utilities
    # ===============================================================
    def _set_vertical_window(self):

        if self.mode == "setpoint":
            # Experience Formula, does not dare to touch it
            self.spec.set_ref_ampl(min(self.amplitude+16, 18))
        else:
            self.spec.set_ref_ampl(int(self.amplitude)+5 * self._divA)

    def _convert_frequency_value(self, frequency):

        min_hz = RF_SYSTEM_PARAMS["frequency_min"]
        max_hz = RF_SYSTEM_PARAMS["frequency_max"]

        if frequency >= min_hz and frequency <= max_hz:
            return frequency
        elif frequency >= min_hz/1e9 and frequency <= max_hz/1e9:
            return frequency * 1e+9
        else:
            raise ValueError("Frequency is not supported! Supported range: [1e+6, 31.8e+9]")

    def _auto_setpoint(self, target: float):

        _max_iter = 15
        _tol = 0.002
        _n_meas = 3
        _settle_time = 0.05

        if self._last_setpoint is None:
            self._last_setpoint = self._get_initial_setpoint(target)

        for k in range(_max_iter):
            self.generator.set_ampl(self._last_setpoint)
            time.sleep(_settle_time)

            measured_amplitudes = np.zeros(_n_meas)
            for i in range(_n_meas):
                measured_amplitudes[i] = self.get_amplitude()

            act_ampl = np.mean(np.sort(measured_amplitudes)[1:-1])
            err = target - act_ampl

            if abs(err) <= _tol:
                print(f"[RFController] RF setpoint: {self._last_setpoint:.3f} dBm")
                return

            self._update_setpoint_fast(err)

        print("[RFController] Warning: Did not find proper setpoint for this RF_amplitude within "
             f"setpoint bound [{self._setpoint_min:.3f}, {self._setpoint_max:.3f}] dBm!\n"
             f"[RFController] Using setpoint: {self._last_setpoint:.3f} dBm! Actual amplitude: {act_ampl:.3f} dBm.")

    def _update_setpoint(self, err: float):
        """
        Robust setpoint update
        If RF system changed, either use this or write a new fast algorithm.
        """

        self._last_setpoint += 0.9 * err
        self._last_setpoint = max(self._setpoint_min, min(self._setpoint_max, self._last_setpoint))

    # 3.1) RF System dependent Functions, Modify when Changed
    # ===============================================================
    def _get_initial_setpoint(self, target: float) -> float:

        # This has to change when the RF connection system or trap was changed.
        # Not deadly if not changed, though
        if target <= 10.2:
            return target - 10.2
        elif target <= 12.2:
            return 2.0 * (target - 10.2)
        elif target <= 12.8:
            return 3.33 * (target - 12.2) + 4.0
        else:
            return 8.0

    def _update_setpoint_fast(self, err: float):

        # Semi-Newton's Method
        if self._last_setpoint <= 0.0: K = 1.0
        elif self._last_setpoint <= 4.0: K = 2.0
        elif self._last_setpoint <= 6.0: K = 3.33
        else: K = 5.0

        self._last_setpoint += K * err
        self._last_setpoint = max(self._setpoint_min, min(self._setpoint_max, self._last_setpoint))

    # 4) Utilities
    # ===============================================================
    def set_mode(self, mode):
        self.mode = mode

    def set_marker_no(self, marker_no):
        self.marker_no = marker_no

    def set_frequency(self, frequency = None):

        if frequency is not None:
            self.frequency = self._convert_frequency_value(frequency)

        self.generator.set_freq(self.frequency)
        self.spec.set_center_freq(self.frequency)

    def set_amplitude(self, amplitude = None):

        if amplitude is not None:
            self.amplitude = amplitude

        if self.mode == "setpoint":
            self.generator.set_ampl(self.amplitude)
        else:
            self._auto_setpoint(self.amplitude)

        self._set_vertical_window()

    def measure(self):
        frequency, amplitude, _ = self.spec.marker_measure(self.marker_no)
        return frequency, amplitude

    def get_frequency(self) -> float:
        return self.spec.marker_measure(self.marker_no)[0]

    def get_amplitude(self) -> float:
        return self.spec.marker_measure(self.marker_no)[1]
