from artiq.experiment import *
class Time(EnvExperiment):
  def build(self):
    self.setattr_device("core")
    self.setattr_device("ttl0")
  @kernel
  def run(self):
    self.core.reset()
    self.ttl0.output()
    for i in range(1000000):
      delay(2*us)
      self.ttl0.pulse(2*us)
