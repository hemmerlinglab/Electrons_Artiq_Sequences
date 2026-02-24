from base_instruments import BaseVisaInstrument
import time

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

    def __init__(self, IP="192.168.42.181"):
        super().__init__(IP)
        self.mode = None

    # -------------------------------------------------------------------------
    # Output control
    # -------------------------------------------------------------------------
    def on(self, channel=1):
        self.write(f":OUTPut{channel}:STATe ON")

    def off(self, channel=1, disable_output=True, kill_socket=False):
        if disable_output:
            self.write(f":OUTPut{channel}:STATe OFF")
        if kill_socket:
            super().close()

    # -------------------------------------------------------------------------
    # Function / waveform
    # -------------------------------------------------------------------------
    def set_function(self, channel, function):
        self.write(f":SOURce{channel}:FUNCtion {function}")

    def set_frequency(self, channel, frequency):
        # frequency unit: Hz
        self.write(f":SOURce{channel}:FREQuency {float(frequency)}")

    def set_voltage_high(self, channel, voltage):
        # voltage unit: V
        self.write(f":SOURce{channel}:VOLTage:HIGH {float(voltage)}")

    def set_voltage_low(self, channel, voltage):
        # voltage unit: V
        self.write(f":SOURce{channel}:VOLTage:LOW {float(voltage)}")

    def set_pulse_duty(self, channel, duty):
        # duty unit: percentage
        self.write(f":SOURce{channel}:FUNCtion:PULSe:DCYCle {float(duty)}")

    def set_pulse_width(self, channel, width):
        # width unit: s
        self.write(f":SOURce{channel}:PULSe:WIDTh {float(width)}")

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

    def set_burst_trigger_source(self, channel, source):
        # source: INTernal | EXTernal | MANual
        self.write(f":SOURce{channel}:BURSt:TRIGger:SOURce {source}")

    def set_burst_trigger_slope(self, channel, slope):
        # slope: POSitive | NEGative
        self.write(f":SOURce{channel}:BURSt:TRIGger:SLOPe {slope}")

    def burst_trigger_immediate(self, channel):
        self.write(f":SOURce{channel}:BURSt:TRIGger:IMMediate")

    # -------------------------------------------------------------------------
    # Special Commands
    # -------------------------------------------------------------------------
    def send_force_reset(self):
        if self.mode == "force rst":
            self.burst_trigger_immediate(1)
            time.sleep(0.001)
        else:
            print("[DG4162] Current mode is incorrect, ignoring command!")

    # -------------------------------------------------------------------------
    # Preset: Channel 1 Modes for signal and reset
    # -------------------------------------------------------------------------
    def config_general(self):
        """General Initialization when ARTIQ stats"""
        channel = 1
        self.set_function(channel, "PULSe")
        self.set_burst_state(channel, True)
        self.set_burst_mode(channel, "TRIGgered")
        self.set_burst_trigger_slope(channel, "POSitive")

    def set_to_signal_mode(self):
        """
        Configure Channel 1 for burst pulse output:
        - Pulse waveform
        - Burst mode ON
        - freq=700 kHz, High=5 V, Low=0 V, Duty=30%
        - output ON by default
        """
        channel = 1
        self.mode = "signal"
        self.set_frequency(channel, 700e3)
        self.set_voltage_high(channel, 5.0)
        self.set_voltage_low(channel, 0.0)
        self.set_pulse_duty(channel, 30.0)
        self.set_burst_ncycles(channel, 1)
        self.set_burst_trigger_source(channel, "EXTernal")

        self.on(channel)

    def set_to_force_rst_mode(self):
        """
        Configuration for forcefully resetting the envelop threshold detector
        """
        channel = 1
        self.mode = "force rst"
        self.set_frequency(channel, 20e3)
        self.set_pulse_duty(channel, 10.0)
        self.set_voltage_high(channel, 5.0)
        self.set_voltage_low(channel, 0.0)
        self.set_burst_ncycles(channel, 5)
        self.set_burst_trigger_source(channel, "MANual")

        self.on(channel)

################################################################
# Testing Code
################################################################

if __name__ == "__main__":

    fg = DSG821()

    fg.id()

    fg.set_freq(8.0)
    fg.set_ampl(0.0)

    fg.close()

if __name__ == "__main__":
    dg = DG4162()
    dg.id()

    dg.config_general()
    dg.set_to_force_rst_mode()
    dg.send_force_reset()
    dg.set_to_signal_mode()

    dg.close()