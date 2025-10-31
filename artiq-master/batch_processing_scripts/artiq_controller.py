import subprocess
import copy
import re

class ArtiqController:

    def __init__(self, script_path: str, command: str = "artiq_run"):
        self.exp_params = {}
        self.command = command
        self.script = script_path

    def set_command(self, command: str):
        self.command = command

    def set_script(self, script_path: str):
        self.script = script_path

    def set_param(self, key: str, val):
        self.exp_params[key] = val

    def load_params(self, conf: dict):
        self.exp_params.update(conf)

    def delete_param(self, key: str):
        self.exp_params.pop(key, None)

    def clear_params(self):
        self.exp_params.clear()

    def get_params(self):
        return copy.deepcopy(self.exp_params)

    def _construct_args(self):
        args = [self.command, "-q", self.script]
        for key, value in self.exp_params.items():
            args.append(f"{key}={repr(value)}")
        return args

    def _extract_timestamps(self, cp) -> str:
        return re.search(r"(\d{8}_\d{6})", cp.stdout).group(1)

    def print_args(self):
        print(self._construct_args())

    def run(self) -> str:
        cp = subprocess.run(
            self._construct_args(),
            capture_output=True,
            text=True
        )
        return self._extract_timestamps(cp)

if __name__ == "__main__":
    ac = ArtiqController("general_scan.py")
    ac.set_param("time_count", 0.5)
    ac.set_param("mesh_voltage", 120)
    ac.set_param("scanning_parameter", "tickle_frequency")
    ac.set_param("min_scan", 1)
    ac.set_param("max_scan", 150)
    ac.set_param("steps", 150)
    ac.print_args()

"""
cmd = 'artiq_run -q ../Electrons/Scan_DC_electrodes.py time_count=' + str(time_count) + ' mesh_voltage=' + str(mesh_voltage) + ' Zotino_channel=' + str(elec_dict[e]) + ' minimum=' + str(min_volt) + ' maximum=' + str(max_volt) + ' steps=' + str(steps)
"""