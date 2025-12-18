from artiq.experiment import *
import matplotlib.pyplot as plt
import sys

sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from dc_electrodes import Electrodes
from base_sequences import set_multipoles

class ApplySpecificMultipole(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('zotino0')

        self.setattr_argument('trap', EnumerationValue(["Single PCB", "UCB 3 PCB"], default="Single PCB"))
        self.setattr_argument('flip_electrode', BooleanValue(default=False))
        self.setattr_argument('U1', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('U2', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('U3', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('U4', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('U5', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('Ex', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('Ey', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))
        self.setattr_argument('Ez', NumberValue(default=0.0,unit='',scale=1,ndecimals=3,step=0.001))

    def prepare(self):
        self.electrodes = Electrodes(trap=self.trap, flipped=self.flip_electrode)

        self.multipole_vector = {
            "U1": self.U1,
            "U2": self.U2,
            "U3": self.U3,
            "U4": self.U4,
            "U5": self.U5,
            "Ex": self.Ex,
            "Ey": self.Ey,
            "Ez": self.Ez,
        }

        self.electrodes.print_voltage_matrix(self.multipole_vector)

    def analyze(self):
        self.electrodes.plot_voltage_heatmap(self.multipole_vector)

    def run(self):

        self.core.reset()
        set_multipoles(self)
