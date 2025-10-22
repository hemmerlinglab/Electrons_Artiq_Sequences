from artiq.experiment import *

class Individual_Zotino_Control(EnvExperiment):

    def build(self):

        self.setattr_device('core')
        self.setattr_device('zotino0')

        self.setattr_argument('channel', NumberValue(default=0,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('output', NumberValue(default=0,unit='V',scale=1,ndecimals=2,step=0.01))

    @kernel
    def zotino_out(self, channel, level):

        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us)
        self.zotino0.write_gain_mu(channel, 65535)
        self.zotino0.write_dac(channel, level)
        self.zotino0.load()

        return

    def run(self):

        self.core.reset()
        self.zotino_out(self.channel, self.output)
