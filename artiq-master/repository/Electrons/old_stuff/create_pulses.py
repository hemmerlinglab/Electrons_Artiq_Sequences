#Create TTL Pulses

from artiq.experiment import *

class Create_Pulses(EnvExperiment):
	def build(self):
		self.setattr_device("core")
		self.setattr_device("ttl6")
		#self.setattr_device('scheduler') # scheduler used
	
	@kernel
	def Pulses(self):
		self.core.reset()
		self.ttl6.output()
		for i in range(1000000):
			delay(5*ms)
			self.ttl6.pulse(10*ms)

	def run(self):
    	    while True:
                #self.scheduler.pause()             # allows for "terminate instances" functionality
                self.Pulses()
