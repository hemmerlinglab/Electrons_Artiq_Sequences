from base_instruments import BaseVisaInstrument

# Rigol DSG821 Function Generator
class DSG821(BaseVisaInstrument):

    # electron rigol IP: .65
    # molecules rigol IP: .46

    def __init__(self, IP='192.168.42.65'):
        super().__init__(IP)

    def set_freq(self, freq):
        self.write(':FREQ {0}MHz'.format(float(freq)))

    def set_ampl(self, level):
        self.write(':LEV {0}'.format(float(level)))

    def on(self):
        self.write(':OUTP ON')

    def off(self):
        self.write(':OUTP OFF')

    def close(self):
        super().close()


# Rigol DG4162 160 MHz Dual-Channel Function/Arbitrary Waveform Generator
class DG4162(BaseVisaInstrument):
    """
    Rigol DG4162 function generator driver.
    Channel numbers are 1 or 2.
    """

    def __init__(self, IP="192.168.42.181"):
        super().__init__(IP)

    # -------------------------------------------------------------------------
    # Output control
    # -------------------------------------------------------------------------
    def on(self, channel=1):
        """Enable output for the specified channel."""
        self.write(f":OUTPut{channel}:STATe ON")

    def off(self, channel=1):
        """Disable output for the specified channel."""
        self.write(f":OUTPut{channel}:STATe OFF")

    # -------------------------------------------------------------------------
    # Function / waveform
    # -------------------------------------------------------------------------
    def set_function(self, channel, func):
        """
        Set waveform function.
        func: 'SINusoid', 'SQUare', 'TRIangle', 'RAMP', 'PULSe', 'NOISe', 'DC', 'ARB'
        """
        self.write(f":SOURce{channel}:FUNCtion {func}")

    def set_frequency(self, channel, freq_hz):
        """Set frequency in Hz (float or int)."""
        self.write(f":SOURce{channel}:FREQuency {float(freq_hz)}")

    def set_voltage_high(self, channel, volts):
        """Set high level voltage (V)."""
        self.write(f":SOURce{channel}:VOLTage:HIGH {float(volts)}")

    def set_voltage_low(self, channel, volts):
        """Set low level voltage (V)."""
        self.write(f":SOURce{channel}:VOLTage:LOW {float(volts)}")

    def set_pulse_duty(self, channel, duty_percent):
        """Set pulse duty cycle (0–100%)."""
        self.write(f":SOURce{channel}:FUNCtion:PULSe:DCYCle {float(duty_percent)}")

    # -------------------------------------------------------------------------
    # Burst mode
    # -------------------------------------------------------------------------
    def set_burst_state(self, channel, on=True):
        """Enable or disable burst mode."""
        state = "ON" if on else "OFF"
        self.write(f":SOURce{channel}:BURSt:STATe {state}")

    def set_burst_mode(self, channel, mode):
        """
        Set burst mode type.
        mode: 'TRIGgered' (N-cycle) or 'GATed'
        """
        self.write(f":SOURce{channel}:BURSt:MODE {mode}")

    def set_burst_ncycles(self, channel, n):
        """
        Set number of cycles per burst (1 to 1000000).
        Use 'INFinity' for continuous burst.
        """
        if isinstance(n, str) and n.upper() == "INFINITY":
            self.write(f":SOURce{channel}:BURSt:NCYCles INFinity")
        else:
            self.write(f":SOURce{channel}:BURSt:NCYCles {int(n)}")

    # -------------------------------------------------------------------------
    # Preset: Channel 1 with your specified configuration
    # -------------------------------------------------------------------------
    def configure_ch1_pulse_burst(
        self,
        freq_hz=700e3,
        high_v=5.0,
        low_v=0.0,
        duty_percent=30.0,
        burst_ncycles="INFinity",
        output_on=True,
    ):
        """
        Configure Channel 1 for burst pulse output:
        - Pulse waveform
        - Burst mode ON
        - freq=700 kHz, High=5 V, Low=0 V, Duty=30%
        - output ON by default
        """
        ch = 1
        self.set_function(ch, "PULSe")
        self.set_frequency(ch, freq_hz)
        self.set_voltage_high(ch, high_v)
        self.set_voltage_low(ch, low_v)
        self.set_pulse_duty(ch, duty_percent)
        self.set_burst_state(ch, True)
        self.set_burst_mode(ch, "TRIGgered")
        self.set_burst_ncycles(ch, burst_ncycles)
        if output_on:
            self.on(ch)


################################################################
# Testing Code
################################################################

if __name__ == "__main__":

    fg = DSG821()

    fg.id()

    fg.set_freq(8.0)
    fg.set_ampl(0.0)

    fg.close()

    dg = DG4162()
    dg.id()
    dg.configure_ch1_pulse_burst()
    dg.close()
