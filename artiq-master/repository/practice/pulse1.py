from artiq.experiment import *
class Pulse1(EnvExperiment):
  def build(self):
    self.setattr_device("core")
    self.setattr_device("ttl4")
   # self.setattr_device('scheduler')
  @kernel
  def run(self):
    self.core.reset()
    self.ttl4.output()
    for i in range(1000000):
     # self.scheduler.pause()
      delay(3*us)
      self.ttl4.pulse(2*us)
