import numpy as np
from traps import traps
import os
import matplotlib.pyplot as plt
from helper_functions import adjust_control_voltages

class VoltageSafetyError(ValueError):
    pass

class Electrodes(object):

    def __init__(self, trap = "UCB 3 PCB", flipped = False):

        if flipped: self.trap = trap + " Flipped"
        else: self.trap = trap

        # Read in trap info
        info = traps[self.trap]
        self.amp = info["amp"]
        self.elec_dict = info["elec_zotino_chs"]
        self.multipoles = info["multipoles_order"]
        self.elec_list = info["electrodes_order"]
        self.voltage_ratings = info["elec_voltage_ratings"]
        self._read_in_cfile(info["cfile"])

        # DC offset voltages
        self.offset_voltages = {}
        for elec in self.elec_dict:
            self.offset_voltages[elec] = 0.0

    # 1) Internal Methods
    #================================================================
    def _read_in_cfile(self, filename):

        # C file path
        base_dir = os.path.dirname(__file__)
        fullpath = os.path.join(base_dir, "Cfiles", filename)

        # Read C file text
        with open(fullpath, 'r') as f:
            Cfile_text = f.read().split('\n')[:-1]

        # Under current C file, this is not impacting anything.
        head = []
        body = []
        for i in range(len(Cfile_text)):
            if Cfile_text[i].find(':') >= 0: head.append(Cfile_text[i])
            else: body.append(Cfile_text[i].split())

        num_columns = 1 # this needs to change if the cfile has more than one column

        # Construct multipole matrix based on data in C file
        self.multipole_matrix = {
            elec: {
                mult: 
                        [
                            float(body[eindex + mindex*len(self.elec_dict)][i]) for i in range(num_columns)
                        ] for mindex, mult in enumerate(self.multipoles)
                } for eindex, elec in enumerate(self.elec_list)
            }

    def _get_voltage_matrix(self, multipole_vector):
        
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

        num_columns = 1 # this needs to change if the cfile has more than one column

        # Calculate control voltage matrix, support multi columns C file (not used now)
        voltage_matrix = {}
        for e in self.elec_dict.keys():
            voltage_matrix[e] = [self.offset_voltages[e] for n in range(num_columns)]
            for n in range(num_columns):
                for m in self.multipoles:
                    voltage_matrix[e][n] += self.multipole_matrix[e][m][n] * multipole_vector[m]

        # Make sure calculated control voltage is not exceeding voltage rating
        self._check_safety(voltage_matrix)

        # Construct lists that can be used by Zotino
        channel_list = []
        voltage_list = []
        for k in voltage_matrix.keys():
            channel_list.append(self.elec_dict[k])
            voltage_list.append(voltage_matrix[k][0])
        
        return (np.array(channel_list, dtype = int), np.array(voltage_list, dtype = float))

    def _check_safety(self, voltage_matrix):

        for elec, voltages in voltage_matrix.items():
            voltage = voltages[0]
            limit = self.voltage_ratings[elec]
            if abs(voltage) > limit:
                raise VoltageSafetyError(
                    f"SAFETY VIOLATION: Electrode {elec} is set to {voltage:.2f} V, "
                    f"which exceeds its limit of +/- {limit:.2f} V!"
                )

    # 2) Usages
    #================================================================
    def set_offset(self, elec, voltage):
        """
        Set DC voltage offset of single electrode.
        """

        if elec not in self.elec_dict:
            raise ValueError(f"Electrode {elec} not found in current trap ({self.trap}).")
        self.offset_voltages[elec] = voltage

    def get_control_voltage(self, multipole_vector, amp=None):
        """
        Get the channel list and voltage list that can be used for Zotino
        """

        # Enables user to override amplifier usage based on actual experimental setup
        if amp is None:
            amp = self.amp

        # Calculate voltages and calibrate using helper_functions
        vec = self._get_voltage_matrix(multipole_vector)
        control_signal = adjust_control_voltages(vec, amp)

        return control_signal

    # 3) Debugging / Testing Tools (Trap Sensitive)
    #================================================================
    def print_voltage_matrix(self, multipole_vector):
        
        inds, vols = self._get_voltage_matrix(multipole_vector)

        for i in range(len(inds)):
            print(f"ch{inds[i]}:\t{vols[i]:6.2f}V")
        print()

    def get_voltage_grid(self, multipole_vector):
        ch_ids, ch_vols = self._get_voltage_matrix(multipole_vector)
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
        ch_ids, ch_vols = self._get_voltage_matrix(multipole_vector)
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
