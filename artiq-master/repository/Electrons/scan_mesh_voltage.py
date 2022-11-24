''' Differences from V3: 
 - no more hard coded detection time, dont forget to recompute all arguments'''

import sys
import os
# import datetime
# import select
from artiq.experiment import *
# from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np
sys.path.append("/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions")
from helper_functions import *



#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')

# Class which defines the pmt counting experiment
class Scan_Mesh_Voltage(EnvExperiment):
    def build(self):
        
         self.config_dict = []
         
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl3') # where pulses are being sent in by ttl
         self.setattr_device('ttl16') # where pulses are being sent in by ttl
         self.setattr_device('zotino0') # where pulses are being sent in by ttl
         self.setattr_argument('time_count', NumberValue(default=200,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('no_of_averages', NumberValue(default=500,unit='number of averages',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used

         #self.setattr_argument('mesh_voltage', NumberValue(default=150,unit='V',min=0,max=600,scale=1,ndecimals=1,step=1))
         self.my_setattr('min_volt', NumberValue(default=0,unit='V',scale=1,ndecimals=1,step=1))
         self.my_setattr('max_volt', NumberValue(default=200,unit='V',scale=1,ndecimals=1,step=1))
         self.my_setattr('step_volt', NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
 
    def my_setattr(self, arg, val):
        
        # define the attribute
        self.setattr_argument(arg,val)

        # add each attribute to the config dictionary
        if hasattr(val, 'unit'):
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + ", 'unit' : '" + str(val.unit) + "'})")
        else:
            exec("self.config_dict.append({'par' : arg, 'val' : self." + arg + "})")


    def prepare(self):
        self.set_dataset('count_tot',[0.0]*self.time_count,broadcast=True)
        
        self.set_dataset('scan_result',[0.0]*self.step_volt,broadcast=True)
        
            
        self.scan_values = self.min_volt + np.arange(0, self.step_volt) * (self.max_volt - self.min_volt)/self.step_volt

        self.set_dataset('scan_x', self.scan_values, broadcast=True)

        # save sequence file name
        self.config_dict.append({'par' : 'sequence_file', 'val' : os.path.abspath(__file__), 'cmt' : 'Filename of the main sequence file'})

        get_basefilename(self)

        # Set the data going to save
        self.data_to_save = [{'var' : 'scan_x', 'name' : 'scan_x'},
                             {'var' : 'scan_result', 'name' : 'counts'}]


        self.core.reset() # Reset the core

    def analyze(self):
        
        print('saving data...')
        save_all_data(self)

        # overwrite config file with complete configuration
        self.config_dict.append({'par' : 'Status', 'val' : True, 'cmt' : 'Run finished.'})
        save_config(self.basefilename, self.config_dict)

        add_scan_to_list(self)
        
        print('Scan ' + self.basefilename + ' finished.')
        print('Scan finished.')


    @kernel
    def set_mesh_voltage(self, voltage):
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us) # this is important to avoid RTIO underflows

        self.zotino0.write_gain_mu(31, 65000)
        
        self.zotino0.write_dac(31, voltage)
        
        self.zotino0.load()

        return

    @kernel
    def set_all_electrode_voltages(self, voltage):

        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        delay(200*us) # this is important to avoid RTIO underflows

        for k in range(31):

            self.zotino0.write_gain_mu(k, 65000)
        
            self.zotino0.write_dac(k, voltage)
        
            self.zotino0.load()
            
            delay(100*us)

        return

    @kernel
    def counting(self):
        #new_data = [0.0]*self.time_count

        self.core.break_realtime()
        # read the counts and store into a dataset for live updating
        

        data0 = [0] * self.no_of_averages

#        with parallel:
#            with sequential:
#                
#                # trigger of function generator
#                for j in range(self.no_of_averages):
#                    self.ttl6.pulse(50*ns)
#
#                    delay(1*self.detection_time*us)
#
#                    delay(10*us)
#                    
#            with sequential:
#                
#                for j in range(self.no_of_averages):
#                    #register rising edges for detection time
#                    
#                    delay(50*ns)
#
#                    ev = self.ttl3.gate_rising(self.detection_time*us)
#             
#                    data0[j] = self.ttl3.count(ev)
#                    
#                    delay(10*us)
       
        trigger_length = 50.0 * ns

        for j in range(self.no_of_averages):
            with parallel:
                with sequential:
                
                    delay(trigger_length)

                    # trigger of function generator
                    self.ttl16.pulse(trigger_length)

                    delay(1.0*self.detection_time*us)

                    delay(1*us)
                    
                with sequential:
                
                    #register rising edges for detection time
                    
                    delay(trigger_length)

                    ev = self.ttl3.gate_rising(self.detection_time*us)
             
                    data0[j] = self.ttl3.count(ev)
                    
                    delay(1.0*self.detection_time*us)
                    
                    delay(1*us)
                    
                    delay(trigger_length)
       

#        j=0
#        with parallel:
#            with sequential:
#            
#                # trigger of function generator
#            #    self.ttl6.pulse(trigger_length)
#                self.ttl16.pulse(trigger_length)
#
#                delay(1.0*self.detection_time*us)
#
#                delay(10*us)
#                
#            with sequential:
#            
#                #register rising edges for detection time
#                
#                delay(trigger_length)
#
#                ev = self.ttl3.gate_rising(self.detection_time*us)
#         
#                data0[j] = self.ttl3.count(ev)
#                
#                delay(1.0*self.detection_time*us)
#                
#                delay(10*us)
       





        self.set_dataset('counts', (data0), broadcast = True)


            
    #@rpc(flags={'async'})
    #def pc(self,new_data):

    #    self.set_dataset('count_tot',new_data, broadcast=True)



    def run(self):
        
        self.core.reset()
        
        self.set_mesh_voltage( 0.0 )

        self.set_all_electrode_voltages( 0.0 )
        
        print('Sleeping for 1 seconds ...')
        time.sleep(1)

        counter = 0

        self.counts = 0
        self.avg_counts = 0

            
        for k in range(self.step_volt):

            print(k)
            self.mesh_voltage = self.scan_values[k]

            self.set_mesh_voltage( 1.0/200.0 * self.mesh_voltage )

            self.scheduler.pause() # allows for "terminate instances" functionality
            
            self.counting()

            cts = np.array(self.get_dataset('counts'))

            self.avg_counts = np.mean(cts)
                    
            self.mutate_dataset('count_tot', counter % self.time_count, self.avg_counts)
            
            self.mutate_dataset('scan_result', k, self.avg_counts )
   
            counter += 1

        print('Setting mesh voltage to 0V')

        self.set_mesh_voltage( 0.0 )

        print('End of scan.')


