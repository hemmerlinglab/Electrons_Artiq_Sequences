import numpy as np
import os.path
import datetime
import shutil
from configparser import ConfigParser
import socket

coeffs = [[1.0077215015216578, 0.07811119205370878],
          [1.0075886011780560, 0.08289830354058464],
          [1.0075997808322728, 0.07742944878884093],
          [1.0074152098184440, 0.08096433237835912],
          [1.0075783030224060, 0.08500852404547181],
          [1.0077047280815805, 0.07119983735967236],
          [1.0075663244423791, 0.08438372527685246],
          [1.0077414112619870, 0.07868868162783679],
          [1.0074178401380516, 0.08086861164982892],
          [1.0075504688409418, 0.08443030102739490],
          [1.0075852020080514, 0.07714037808703461],
          [1.0075733302720014, 0.08740706511678514],
          [1.0075504688409418, 0.08443030102739490],
          [1.0075557875559487, 0.08467066609544131],
          [1.0075878395101907, 0.08716849050007253],
          [1.0074405948638074, 0.08307732043788590],
          [1.0074703864817245, 0.08854904293842517],
          [1.0076119490599504, 0.08956976627865920],
          [1.0074139953453658, 0.08177975464776269],
          [1.0075372698582397, 0.08457306649885853],
          [1.0074166130733675, 0.08158809064438279],
          [1.0072912542796548, 0.08282446811022075],
          [1.0074047012623315, 0.08144315467468566],
          [1.0074380714046611, 0.08398859200469533],
          [1.0074099995608252, 0.08153955186713863],
          [1.0073940985401852, 0.08120239164685718],
          [1.0074543954512805, 0.07746556351445066],
          [1.0074329427174225, 0.08518746512357839],
          [1.0074768749194494, 0.07756334844579837],
          [1.0074287202423378, 0.08322020347259235],
          [1.0072965136381062, 0.08263305942136216],
          [1.0075385853350394, 0.08452520510992840]]


def get_laser_frequencies():

    #print('Getting laser frequencies ...')
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ('192.168.42.20', 62200)

    sock.connect(server_address)

    try:
    
        # Send data
        message = 'request'
        #print('sending "%s"' % message)
        sock.sendall(message.encode())

        len_msg = int(sock.recv(2).decode())

        data = sock.recv(len_msg)

    finally:
        sock.close()

    # return a list of freqs
    # currently only one frequency is returned
    freqs = float(data.decode())

    return freqs


def switch_fiber_channel(channel):

    #print('Getting laser frequencies ...')
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    server_address = ('192.168.42.20', 65000)

    sock.connect(server_address)

    sock.sendall(str(channel).encode())
    sock.close()

    return



def get_basefilename(self, extension = ''):
    my_timestamp = datetime.datetime.today()
    
    self.today = datetime.datetime.today()
    self.today = self.today.strftime('%Y%m%d')

    self.datafolder = '/home/electrons/software/data/'

    basefolder = str(self.today) # 20220707
    # create new folder if doesn't exist yet
    if not os.path.exists(self.datafolder + basefolder):
        os.makedirs(self.datafolder + basefolder)

    self.scan_timestamp = str(my_timestamp.strftime('%Y%m%d_%H%M%S'))

    self.basefilename = self.datafolder + basefolder + '/' + self.scan_timestamp # 20220707_150655

def save_all_data(self):
    # loops over data_to_save and saves all data sets in the array self.data_to_save
    for hlp in self.data_to_save:
        # transform into numpy arrays
        arr = np.array(self.get_dataset(hlp['var']))
       
        # Write Data to Files
        f_hlp = open(self.basefilename + '_' + hlp['var'],'w')
        np.savetxt(f_hlp, arr, delimiter=",")
        f_hlp.close()



def add_scan_to_list(self):
    # Write Data to Files
    f_hlp = open(self.datafolder + '/' + self.today + '/' + 'scan_list_' + self.today, 'a')
    f_hlp.write(self.scan_timestamp + '\n')
    f_hlp.close()


def save_config(basefilename, var_dict):

        # save run configuration
        # creates and overwrites config file
        # var_dict is an array of dictionaries
        # var_dict[0] = {
        #    'par': <parameter name>,
        #    'val': <parameter value>,
        #    'unit': <parameter unit>, (optional)
        #    'cmt': <parameter comment> (optional)
        #    }

        optional_parameters = ['unit', 'cmt']        
        conf_filename = basefilename + '_conf'

        # use ConfigParser to save config options
        config = ConfigParser()

        # create config file
        conf_file = open(conf_filename, 'w')
        print('Config file written.')

        # add scan name to config file
        config['Scan'] = {'filename' : basefilename}

        # toggle through dictionary and add the config categories
        for d in var_dict:
            config[d['par']] = {'val' : d['val']}

            for opt in optional_parameters:
                if opt in d.keys():
                    config[d['par']].update({opt : d[opt]})

        config.write(conf_file)

        # save also the sequence file 
        #print(config['sequence_file']['val'])
        #print(basefilename + '_sequence')
        shutil.copyfile(config['sequence_file']['val'], basefilename + '_sequence')
        
        conf_file.close()
        
def get_optimal_frequencies(mesh_voltage):

    return freq_422, freq_390


def adjust_set_volt(chan, volt):

#    coeffs = [[1.0077215015216578, 0.07811119205370878],
#              [1.0075886011780560, 0.08289830354058464],
#              [1.0075997808322728, 0.07742944878884093],
#              [1.0074152098184440, 0.08096433237835912],
#              [1.0075783030224060, 0.08500852404547181],
#              [1.0077047280815805, 0.07119983735967236],
#              [1.0075663244423791, 0.08438372527685246],
#              [1.0077414112619870, 0.07868868162783679],
#              [1.0074178401380516, 0.08086861164982892],
#              [1.0075504688409418, 0.08443030102739490],
#              [1.0075852020080514, 0.07714037808703461],
#              [1.0075733302720014, 0.08740706511678514],
#              [1.0075504688409418, 0.08443030102739490],
#              [1.0075557875559487, 0.08467066609544131],
#              [1.0075878395101907, 0.08716849050007253],
#              [1.0074405948638074, 0.08307732043788590],
#              [1.0074703864817245, 0.08854904293842517],
#              [1.0076119490599504, 0.08956976627865920],
#              [1.0074139953453658, 0.08177975464776269],
#              [1.0075372698582397, 0.08457306649885853],
#              [1.0074166130733675, 0.08158809064438279],
#              [1.0072912542796548, 0.08282446811022075],
#              [1.0074047012623315, 0.08144315467468566],
#              [1.0074380714046611, 0.08398859200469533],
#              [1.0074099995608252, 0.08153955186713863],
#              [1.0073940985401852, 0.08120239164685718],
#              [1.0074543954512805, 0.07746556351445066],
#              [1.0074329427174225, 0.08518746512357839],
#              [1.0074768749194494, 0.07756334844579837],
#              [1.0074287202423378, 0.08322020347259235],
#              [1.0072965136381062, 0.08263305942136216],
#              [1.0075385853350394, 0.08452520510992840]]

    adjusted_volt = coeffs[chan][0] * volt + coeffs[chan][1]
    #print("adjusted input:", adjusted_volt)

    return adjusted_volt
