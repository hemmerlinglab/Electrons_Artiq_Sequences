from artiq.experiment import *
import numpy as np
import time

class Save2(EnvExperiment):
    def build(self):
        pass  # no devices used

    def run(self):
        self.set_dataset("save2", np.full(10, np.nan), broadcast=True)
        for i in range(10):
            self.mutate_dataset("save2", i, i*i)
            time.sleep(0.5)
        self.get_dataset("save2")
        self.array = np.array(self.get_dataset("save2"))
        print("Dataset as array:", self.array)
        
        
    def analyze(self):
        f = open("s2","w")
        for i in range(len(self.array)):
            f.write(str(self.array[i])+"\n")
        
        f.flush()
        f.close()
        
        
