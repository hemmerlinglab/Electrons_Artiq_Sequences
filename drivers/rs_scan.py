import socket
import time
import numpy as np

class RS:
    
    def __init__(self):

        TCP_IP = '192.168.42.108'
        TCP_PORT = 5025

        self.command_delay = 0.1

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        s.connect((TCP_IP,TCP_PORT))
    
        s.send(b"*IDN?\n")
        t = s.recv(1024)
    
        print(t)
        
        self.socket = s
    
    def send(self, msg):

        send_msg = msg + '\n'

        self.socket.send(send_msg.encode())

        time.sleep(self.command_delay)

    def recv(self):

        self.msg = self.socket.recv(1024)

        return self.msg

    def on(self):

        self.send('OUTP ON')        

    def off(self):

        self.send('OUTP OFF')

    def set_freq(self, freq):

        self.send('FREQ ' + str(freq) + ' Hz')

    def set_ampl(self, ampl):

        self.send(':POW ' + str(ampl))

    def close(self):

        self.socket.close()




class Keysight:
    
    def __init__(self):

        TCP_IP = '192.168.42.63'
        TCP_PORT = 5025

        self.command_delay = 0.01

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        s.connect((TCP_IP,TCP_PORT))
    
        s.send(b"*IDN?\n")
        t = s.recv(1024)
    
        print(t)
        
        self.socket = s
    

    def send(self, msg):

        send_msg = msg + '\n'

        self.socket.send(send_msg.encode())

        time.sleep(self.command_delay)

    def recv(self):

        self.msg = self.socket.recv(1024)

        return self.msg

    def query(self, msg):

        self.send(msg)

        self.msg = self.socket.recv(1024)

        self.msg = self.msg.decode().strip('\n')

        return self.msg


    def set_center_freq(self, freq):

        self.send(':FREQ:CENT ' + str(freq) + ' Hz')

    def set_span(self, span):

        self.send(':FREQ:SPAN ' + str(span) + ' Hz')

    def marker_on(self, no):

        self.send(':CALC:MARK' + str(no) + ':STATE ON')

    def marker_measure(self, no, wait_time = None):

        self.send(':CALC:MARK' + str(no) + ':MAX')

        if not wait_time is None:
            time.sleep(wait_time)

        x = self.query(':CALC:MARK' + str(no) + ':X?')
        
        y = self.query(':CALC:MARK' + str(no) + ':Y?')        
        
        err = self.query(':SYST:ERR?')        

        return (np.float64(x), np.float64(y), err)

    def close(self):

        self.socket.close()




if __name__ == '__main__':
    
    import matplotlib.pyplot as plt
    
    rs = RS()
    
    spec = Keysight()
    
    
    rs.on()
    
    spec.marker_on(1)
    
    x_arr = []
    y_arr = []
    
    
    
    #low_freq = 1e9
    #high_freq = 2.5e9
    
    my_width = 200e6
    
    cnt_freq = 1.570e9
    
    low_freq = cnt_freq - my_width
    high_freq = cnt_freq + my_width
    
    
    steps = 200
    
    
    span_freq = high_freq - low_freq
    cnt_freq = (high_freq + low_freq)/2.0
    
    
    spec.set_center_freq(cnt_freq)
    spec.set_span(span_freq)
    
    
    #spec.set_span(100e6)
    
    
    freq_arr = cnt_freq + np.linspace(-0.5*span_freq,0.5*span_freq,steps)
    
    cnt = 0
    for freq in freq_arr:
    
        print(" Step #: {0} ; Frequency: {1:2.6f} GHz".format(cnt, freq/1e9))
     
        spec.set_center_freq(freq)
    
        rs.set_freq(freq)
    
        (x, y, err) = spec.marker_measure(1, wait_time = 0.2)
    
        print(err)
    
        x_arr.append(x)
        y_arr.append(y)
        
        cnt += 1
    
    rs.off()
    
    rs.close()
    spec.close()
    
    no = 3
    
    f = open('spec_data_x_' + str(no) + '.csv', 'w')
    np.savetxt(f, x_arr, delimiter=",")
    f.close()
    
    f = open('spec_data_y_' + str(no) + '.csv', 'w')
    np.savetxt(f, y_arr, delimiter=",")
    f.close()
    
    
    plt.figure()
    
    plt.plot(x_arr, y_arr)
    
    plt.show()
    
    
    
