import pyvisa as visa

class BaseVisaInstrument:

    def __init__(self, IP):
        self.rm = visa.ResourceManager("@py")
        self.device = self.rm.open_resource('TCPIP::' + IP + '::INSTR')
        return

    def id(self):
        print(self.query('*IDN?'))

    def write(self, msg):
        self.device.write(msg)

    def query(self, msg):
        return self.device.query(msg)

    def wait_finished(self):
        while self.query('*OPC?').strip() != '1':
            pass

    def close(self):
        self.device.close()
