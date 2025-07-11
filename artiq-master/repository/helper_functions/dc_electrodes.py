import numpy as np
from traps import traps
import sys
import matplotlib.pyplot as plt

class Electrodes(object):

    def __init__(self, trap = "UCB 3 PCB", flipped = False):

        if flipped: trap = trap + " Flipped"

        self.elec_dict = traps[trap]["elec_zotino_chs"]
        self.multipoles = traps[trap]["multipoles_order"]
        self.elec_list = traps[trap]["electrodes_order"]
        self.read_in_cfile(traps[trap]["cfile"])

        return


    def read_in_cfile(self, filename):
        
        Cfile_text = open(filename).read().split('\n')[:-1]
        
        head = []
        body = []
        for i in range(len(Cfile_text)):
          if Cfile_text[i].find(':') >= 0: head.append(Cfile_text[i])
          else: body.append(Cfile_text[i].split())

        num_columns = 1 # this needs to change if the cfile has more than one column

        self.multipole_matrix = {
            elec: {
                mult: 
                        [
                            float(body[eindex + mindex*len(self.elec_dict)][i]) for i in range(num_columns)
                        ] for mindex, mult in enumerate(self.multipoles)
                } for eindex, elec in enumerate(self.elec_list)
            }

        return


    def getVoltageMatrix(self, multipole_vector):
        
        # example of multipole vector:
        #
        # multipole_vector = {
        #        'Ex' : 0,
        #        'Ey' : 0,
        #        'Ez' : 0,
        #        'U1' : 0,
        #        'U2' : -1,
        #        'U3' : 0,
        #        'U4' : 0,
        #        'U5' : 0
        #    }

        num_columns = 1
            
        voltage_matrix = {}
        for e in self.elec_dict.keys():
            voltage_matrix[e] = [0. for n in range(num_columns)]
            for n in range(num_columns):
                for m in self.multipoles:
                    voltage_matrix[e][n] += self.multipole_matrix[e][m][n] * multipole_vector[m]

        channel_list = []
        voltage_list = []
        for k in voltage_matrix.keys():

            channel_list.append(self.elec_dict[k])
            voltage_list.append(voltage_matrix[k][0])
        
        return (np.array(channel_list, dtype = int), np.array(voltage_list, dtype = float))


    def print_voltage_matrix(self, multipole_vector):
        
        inds, vols = self.getVoltageMatrix(multipole_vector)

        for i in range(len(inds)):
            print(f"ch{inds[i]}:\t{vols[i]:6.2f}V")
        print()

        return

    def get_voltage_grid(self, multipole_vector):
        ch_ids, ch_vols = self.getVoltageMatrix(multipole_vector)
        volt_by_ch = {int(c): v for c, v in zip(ch_ids, ch_vols)}
        volt_by_name = {name: volt_by_ch.get(ch, np.nan) for name, ch in self.elec_dict.items()}
        row_keys = ['bl', 'br', 'tl', 'tr']
        n_rows, n_cols = 4, 5
        grid = np.full((n_rows, n_cols), np.nan)
        for name, v in volt_by_name.items():
            if len(name) < 3:
                continue
            prefix = name[:2].lower()
            if prefix not in row_keys:
                continue
            try:
                col_idx = int(name[2:]) - 1
            except ValueError:
                continue
            if 0 <= col_idx < n_cols:
                row_idx = row_keys.index(prefix)
                grid[row_idx, col_idx] = v
        return grid, volt_by_name.get('tg', None)


    def plot_voltage_heatmap(self,
                             multipole_vector,
                             cmap='coolwarm',
                             figsize=(5, 4),
                             decimals=2,
                             mode='show'):
        """
        Draw a 4×5 voltage heat-map (rows: bl, br, tl, tr).  
        """
        # 1) volt_by_ch: channel → voltage  (independent of dict order)
        ch_ids, ch_vols = self.getVoltageMatrix(multipole_vector)
        volt_by_ch = {int(c): v for c, v in zip(ch_ids, ch_vols)}

        # 2) volt_by_name: electrode name → voltage, via elec_zotino_chs
        volt_by_name = {
            name: volt_by_ch.get(ch, np.nan)
            for name, ch in self.elec_dict.items()
        }

        # 3) build 4×5 grid (rows fixed order)
        row_keys = ['bl', 'br', 'tl', 'tr']
        n_rows, n_cols = 4, 5
        grid = np.full((n_rows, n_cols), np.nan)

        for name, v in volt_by_name.items():
            if len(name) < 3:
                continue                              # 'tg', needles, etc.
            prefix = name[:2].lower()
            if prefix not in row_keys:
                continue
            try:
                col_idx = int(name[2:]) - 1          # '1'-'5' → 0-4
            except ValueError:
                continue
            if 0 <= col_idx < n_cols:
                row_idx = row_keys.index(prefix)
                grid[row_idx, col_idx] = v

        # 4) guard electrode value for info
        tg_val = volt_by_name.get('tg', None)

        # 5) plotting
        fig, ax = plt.subplots(figsize=figsize)
        vmax = np.nanmax(np.abs(grid))
        im = ax.imshow(grid,
                       cmap=cmap,
                       vmin=-vmax,
                       vmax=vmax,
                       origin='upper',
                       aspect='auto')

        ax.set_xticks(np.arange(n_cols))
        ax.set_yticks(np.arange(n_rows))
        ax.set_xticklabels(np.arange(1, n_cols + 1))
        ax.set_yticklabels(row_keys)
        ax.set_xlabel("Electrode order number")
        ax.set_ylabel("Row of electrodes")

        # title
        nz = [f"{k} = {v:g}" for k, v in multipole_vector.items() if v]
        title = "Generates " + ", ".join(nz) if nz else "Voltage pattern"
        if tg_val is not None and not np.isnan(tg_val):
            title += f"  (tg = {tg_val:.{decimals}f} V)"
        ax.set_title(title)

        # colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Voltage (V)")

        # annotate each cell
        for r in range(n_rows):
            for c in range(n_cols):
                if not np.isnan(grid[r, c]):
                    ax.text(c, r,
                            f"{grid[r, c]:.{decimals}f}",
                            ha='center', va='center', fontsize=8)

        plt.tight_layout()

        if mode == 'show':
            plt.show()
        elif mode == 'return':
            return fig, grid
        else:
            raise ValueError("`mode` must be \'show\' or \'return\'!")




class Flipped_Electrodes(object):


    def __init__(self):

        # connects the Zotino channel number with the electrodes
        self.elec_dict = {
            'tg' : 100,
            'tl1' : 12,
            'tl2' : 13,
            'tl3' : 14,
            'tl4' : 15,
            'tl5' : 16,
            'tr1' : 21,
            'tr2' : 20,
            'tr3' : 19,
            'tr4' : 18,
            'tr5' : 17,
            'bl1' : 0,
            'bl2' : 1,
            'bl3' : 2,
            'bl4' : 3,
            'bl5' : 4,
            'br1' : 9,
            'br2' : 8,
            'br3' : 7,
            'br4' : 6,
            'br5' : 5,
         }
        # needle top: channel 10
        # needle bottom: channel 22
        # GND top: channel 11
        # GND bottom: channel 23
        # GND bottom: channel 24

        
        self.multipoles = ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5']
        self.read_in_cfile('/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/repository/helper_functions/Cfile.txt')


        return

    def read_in_cfile(self, filename):
        
        Cfile_text = open(filename).read().split('\n')[:-1]
        
        head = []
        body = []
        for i in range(len(Cfile_text)):
          if Cfile_text[i].find(':') >= 0: head.append(Cfile_text[i])
          else: body.append(Cfile_text[i].split())


        num_columns = 1 # this needs to change if the cfile has more than one column

        self.multipole_matrix = {
            elec: {
                mult: 
                        [
                            float(body[eindex + mindex*len(self.elec_dict)][i]) for i in range(num_columns)
                        ] for mindex, mult in enumerate(self.multipoles)
                } for eindex, elec in enumerate(sorted(self.elec_dict.keys()))
            }


        return


    def getVoltageMatrix(self, multipole_vector):
        
        # example of multipole vector:
        #
        # multipole_vector = {
        #        'Ex' : 0,
        #        'Ey' : 0,
        #        'Ez' : 0,
        #        'U1' : 0,
        #        'U2' : -1,
        #        'U3' : 0,
        #        'U4' : 0,
        #        'U5' : 0
        #    }


        num_columns = 1
            
        voltage_matrix = {}
        for e in self.elec_dict.keys():
            voltage_matrix[e] = [0. for n in range(num_columns)]
            for n in range(num_columns):
                for m in self.multipoles:
                    voltage_matrix[e][n] += self.multipole_matrix[e][m][n] * multipole_vector[m]

        channel_list = []
        voltage_list = []
        for k in voltage_matrix.keys():

            channel_list.append(self.elec_dict[k])
            voltage_list.append(voltage_matrix[k][0])
        
        return (np.array(channel_list, dtype = int), np.array(voltage_list, dtype = float))


    def print_voltage_matrix(self, multipole_vector):
        
        v = self.populateVoltageMatrix(multipole_vector)
        
        for l in ['t','b']:
            for k in range(5):
        
                    my_key = l+'l'+str(5-k)
                    my_key2 = l+'r'+str(5-k)
        
                    print("{0:3s} : {1:6.2f}     {2:3s} : {3:6.2f}".format(my_key, v[my_key][0], my_key2, v[my_key2][0]))
        
            print()

        return
