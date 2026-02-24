import socket
import time

class BK4053:

    def __init__(self, TCP_IP="192.168.42.64", TCP_PORT=5025, timeout=2.0):

        self.command_delay = 0.05

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((TCP_IP,TCP_PORT))

        self.socket = s
        time.sleep(self.command_delay)

        reply = self.query("*IDN?")
        if "4053" not in reply:
            raise RuntimeError(f"Not BK4053? *IDN? -> {reply!r}")

    def send(self, msg):
        send_msg = msg.rstrip("\r\n") + "\n"
        self.socket.sendall(send_msg.encode("ascii"))
        time.sleep(self.command_delay)

    def recv_line(self, max_bytes=4096):
        chunks = []
        total = 0
        while total < max_bytes:
            chunk = self.socket.recv(256).decode()
            if not chunk: break
            chunks.append(chunk)
            total += len(chunk)
            if "\n" in chunk: break
        return "".join(chunks)

    def query(self, msg):
        self.send(msg)
        return self.recv_line()

    def on(self, channel):
        self.send(f"C{channel}:OUTP ON")        

    def off(self, channel):
        self.send(f"C{channel}:OUTP OFF")
        
    def set_burst_mode(self, channel, burst):
        self.send(f"C{channel}:BTWV STATE, {'ON' if burst else 'OFF'}")

    def set_carr_delay(self, channel, delay):
        self.send(f"C{channel}:BTWV CARR,DLY,{delay}")

    def set_carr_freq(self, channel, frequency):
        self.send(f"C{channel}:BTWV CARR,FRQ,{frequency}")
        
    def set_carr_width(self, channel, freq, width):
        duty = 100 * width / (1/freq)
        self.send(f"C{channel}:BTWV CARR,DUTY,{duty}")
        
    def set_carr_ampl(self, channel, amplitude):
        self.send(f"C{channel}:BTWV CARR,AMP,{amplitude}")

    def set_carr_offset(self, channel, offset):
        self.send(f"C{channel}:BTWV CARR,OFST,{offset}")

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

if __name__ == '__main__':
    bk = BK4053()
    bk.close()
