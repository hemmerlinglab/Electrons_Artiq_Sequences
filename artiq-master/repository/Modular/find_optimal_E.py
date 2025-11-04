from artiq.experiment import EnvExperiment, BooleanValue, NumberValue, EnumerationValue
import sys

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from base_functions import load_variables, load_attributes, my_setattr

class FindOptimalE(EnvExperiment):

    def build(self):

        load_variables(self)
        load_attributes(self)

        # Initialize Arguments
        # Diff: No counting mode, no short detection mode, tickle is kept off
        # 1. Histogram
        my_setattr(self, 'histogram_on',      BooleanValue(default=True), scanable=False)
        my_setattr(self, 'bin_width',         NumberValue(default=1.0,unit='us',scale=1,ndecimals=1,step=0.1), scanable = False)
        my_setattr(self, 'histogram_refresh', NumberValue(default=1000,unit='',scale=1,ndecimals=0,step=1), scanable = False)

        # 2. Detector
        my_setattr(self, 'mesh_voltage', NumberValue(default=120,unit='V',scale=1,ndecimals=0,step=1))
        my_setattr(self, 'MCP_front',    NumberValue(default=400,unit='V',scale=1,ndecimals=0,step=1))

        # 3. Sequence
        my_setattr(self, 'wait_time',      NumberValue(default=90,unit='us',scale=1,ndecimals=0,step=1))
        my_setattr(self, 'load_time',      NumberValue(default=210,unit='us',scale=1,ndecimals=0,step=1))
        my_setattr(self, 'no_of_repeats',  NumberValue(default=10000,unit='',scale=1,ndecimals=0,step=1))
        my_setattr(self, 'detection_time', NumberValue(default=1000,unit='ms for counting mode only',scale=1,ndecimals=0,step=1))

        # 4. Trap
        my_setattr(self, 'trap',            EnumerationValue(list_of_traps,default=list_of_traps[0]), scanable = False)
        my_setattr(self, 'flip_electrodes', BooleanValue(default=False))

        # 5. Lasers
        my_setattr(self, 'frequency_422', NumberValue(default=709.078300,unit='THz',scale=1,ndecimals=6,step=1e-6))
        my_setattr(self, 'frequency_390', NumberValue(default=768.708843,unit='THz',scale=1,ndecimals=6,step=1e-6))

        # 6. RF
        my_setattr(self, 'RF_on', BooleanValue(default=False))
        my_setattr(self, 'RF_amplitude', NumberValue(default=4,unit='dBm',scale=1,ndecimals=1,step=.1))
        my_setattr(self, 'RF_frequency', NumberValue(default=1.732,unit='GHz',scale=1,ndecimals=4,step=.0001))

        # 7. Extraction Pulse
        my_setattr(self, 'ext_pulse_length',    NumberValue(default=900,unit='ns',scale=1,ndecimals=0,step=1))
        my_setattr(self, 'ext_pulse_amplitude', NumberValue(default=15,unit='V',scale=1,ndecimals=2,step=.01))

        # 8. Second Order Multipoles
        my_setattr(self, 'U1', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
        my_setattr(self, 'U2', NumberValue(default=-0.13,unit='V',scale=1,ndecimals=3,step=.001))
        my_setattr(self, 'U3', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
        my_setattr(self, 'U4', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))
        my_setattr(self, 'U5', NumberValue(default=0.0,unit='V',scale=1,ndecimals=3,step=.001))

        # 9. Optimizer
        my_setattr(self, 'optimize_target', EnumerationValue(['trapped count', 'lost count', 'loading count', 'trapped ratio', 'lost ratio'], default='trapped count'), scanable = False)
        my_setattr(self, 'max_iters',       NumberValue(default=30, unit='steps', ndecimals=0), scanable = False)
        my_setattr(self, '')