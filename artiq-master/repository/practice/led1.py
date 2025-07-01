from artiq.experiment import *
class LED1(EnvExperiment):
  def build(self):
    self.setattr_device("core")
    self.setattr_device("led1")
  @kernel
  def run(self):
    self.core.reset()
    self.led1.off()
