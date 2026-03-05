import socket
import time


class LaserClient:

    def __init__(self):

        TCP_IP = "192.168.42.26"
        TCP_PORT = 63700
        self.address = (TCP_IP, TCP_PORT)

        self._create_connection()

    def _create_connection(self):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(self.address)

        # Enable line-based reader
        self.socket = s
        self.rf = s.makefile('r', encoding = "utf-8", newline = "")

    def _reconnect(self):
        self.close()
        self._create_connection()

    def _send(self, message: str):

        if not message.endswith('\n'):
            message += '\n'

        self.socket.sendall(message.encode("utf-8"))

    def _recv(self) -> str:
        """Line based receiving"""

        line = self.rf.readline()
        if not line:
            raise ConnectionResetError("EOF from server")

        return line.rstrip('\r\n')

    def query(self, message: str) -> str:

        try:
            self._send(message)
            return self._recv()

        except (BrokenPipeError, ConnectionResetError, OSError):
            self._reconnect()
            self._send(message)
            return self._recv()

    def set_frequency(self, laserid, setpoint: float, max_attempt: int = 3) -> None:
        """
        Send laser setpoint to the server
        It is fine to use int or str laserid
        """

        respond = None

        for attempt in range(max_attempt):
            respond = self.query(f"{laserid},{setpoint:.6f}")
            if respond == '1':
                print(f"Successfully sent setpoint {setpoint:.6f} THz to laser {laserid}!")
                return

        raise RuntimeError(f"Failed to set laser {laserid} to {setpoint:.6f} THz after {max_attempt} attempts!")

    def switch_laser(self, laserid, max_attempt: int = 3) -> None:
        """
        Switch fiber to laser `laserid` via remote server (e.g. 422, 390).
        Requires servo motor on the Laser Lock GUI side.
        """
        for attempt in range(max_attempt):
            respond = self.query(f"{laserid},switch")
            if respond == "1":
                print(f"Successfully switched to laser {laserid}!")
                return
        raise RuntimeError(f"Failed to switch to laser {laserid} after {max_attempt} attempts!")

    def get_setpoint(self, laserid, max_attempt: int = 3):
        """
        Get current lock setpoint (THz) of laser `laserid` from remote server.
        Returns None if locker not running or laser not configured.
        """
        for attempt in range(max_attempt):
            respond = self.query(f"{laserid},set?")
            if respond == "0":
                return None
            try:
                laserid_recv, setpoint = respond.split(",")
                if laserid_recv != str(laserid):
                    continue
                return float(setpoint)
            except Exception:
                continue
        return None

    def get_frequency(self, laserid, max_attempt: int = 3) -> float:
        """
        Get last wavemeter reading (THz) of laser `laserid` from remote server.
        Warning: returns cached value. If fiber was on another laser, the value may be stale.
        Use switch_and_get_frequency() to switch first and ensure fresh reading.
        """
        respond = None

        for attempt in range(max_attempt):
            respond = self.query(f"{laserid},?")
            try:
                laserid_recv, last_freq = respond.split(',')
                if laserid_recv != str(laserid):
                    print("Mismatched Laser ID!")
                    continue
                return float(last_freq)

            # Difference between `except:` and `except Exception:` is the former will capture `BaseException` like `KeyBoardInterrupt`, `SystemExit`, `GeneratorExit`, etc, which is not good, the latter is good.
            except Exception:
                continue

        print(f"Failed to get last frequency of laser {laserid} after {max_attempt} attempts!")

        return 0.0

    def switch_and_get_frequency(self, laserid, wait_after_switch: float = 1.5, max_attempt: int = 3) -> float:
        """
        Switch to laser `laserid`, wait for servo and wavemeter, then get fresh frequency.
        Use this when you need the current value of a laser that may not be the active one.
        """
        self.switch_laser(laserid, max_attempt=max_attempt)
        time.sleep(wait_after_switch)
        return self.get_frequency(laserid, max_attempt=max_attempt)

    def close(self):

        try: self.rf.close()
        except Exception: pass
        try: self.socket.close()
        except Exception: pass


if __name__ == "__main__":

    laser_controller = LaserClient()

    try:
        for i in range(2):
            reply = laser_controller.set_frequency(422, 709.078240)
            time.sleep(15)

        freq_422 = laser_controller.get_frequency(422)
        print(f"422 frequency: {freq_422:.6f} THz")
        freq_390 = laser_controller.get_frequency(390)
        print(f"390 frequency: {freq_390:.6f} THz")

    finally:
        laser_controller.close()
