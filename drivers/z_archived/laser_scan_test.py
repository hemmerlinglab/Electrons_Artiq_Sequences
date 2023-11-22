import socket
import time

def set_single_laser(frequency):
        
        # Write the frequency value to the file
        # Notice that the default output path of ARTIQ is /artiq-master/results/(date and time)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('192.168.42.136', 63700)

        print('sending new setpoint: ' + str(frequency))
        sock.connect(server_address)
        
        my_str = "{0:.9f}".format(frequency)

        #print(my_str)
        #print(my_str.encode())
        try:
            sock.sendall(my_str.encode())

        finally:

            sock.close()        
        
        return

nu1 = 709.07824
nu2 = 709.07724

for k in range(3):
    set_single_laser(nu1)

    time.sleep(3)

    set_single_laser(nu2)

    time.sleep(3)



