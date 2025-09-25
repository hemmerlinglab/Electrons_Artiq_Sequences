from artiq.experiment import *

class SamplerTest(EnvExperiment):
    
    def build(self):

        # Setup the core
        self.setattr_device("core")

        # Setup devices for test
        self.setattr_device("sampler0")
        self.setattr_device("zotino0")

    @kernel
    def zotino_out(self, channel, level):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(channel, 65000)
        self.zotino0.write_dac(channel, level)
        self.zotino0.load()

        return

    @kernel
    def sampler_read(self):

        self.core.break_realtime()
        self.sampler0.init()
        delay(200*us)

        readings = [0.0] * 8
        self.sampler0.sample(readings)
        self.set_dataset("sampler_voltages", readings, broadcast=True)

    def run(self):

        self.core.reset()

        self.zotino_out(27, 2.7)

        self.sampler_read()
        result = self.get_dataset("sampler_voltages")

        print("Sampler Measurement Results: ")
        print(result)
