import subprocess
import copy
import re
from datetime import datetime
import os

from config import drop_keys

# 1) Master Class
# =============================================================================
class ArtiqController:

    def __init__(
            self,
            script_path: str = None,
            command: str = "artiq_run",
            workdir: str = "/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/",
            log_path: str = "/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/result"
        ):
        self.exp_params = {}
        self.command = command
        self.script = script_path
        self.workdir = workdir    # Must set appropriately otherwise artiq would crash
        self.log_path = log_path

        # In-memory profiles: name -> {"script": ..., "command": ..., "params": {...}}
        self._profiles = {}

    # -----------------------------
    # Basic configuration (fluent)
    # -----------------------------
    def set_command(self, command: str):
        self.command = command
        return self  # allow chaining

    def set_script(self, script_path: str):
        self.script = script_path
        return self

    def set_workdir(self, workdir: str):
        self.workdir = workdir
        return self

    def set_log_path(self, log_path: str):
        self.log_path = log_path
        return self

    def set_param(self, key: str, val):
        self.exp_params[key] = val
        return self

    def load_params(self, conf: dict):
        self.exp_params.update(conf)
        return self

    def delete_param(self, key: str):
        self.exp_params.pop(key, None)
        return self

    def clear_params(self):
        self.exp_params.clear()
        return self

    def get_params(self):
        # non-fluent: you want the dict, not self
        return copy.deepcopy(self.exp_params)

    def get_param(self, param_key, default=None):
        return self.exp_params.get(param_key, default)

    # -----------------------------
    # Profiles / presets
    # -----------------------------
    def save_profile(self, name: str):
        """
        Save current script/command/params under a profile name.
        """
        self._profiles[name] = {
            "script": self.script,
            "command": self.command,
            "workdir": self.workdir,
            "params": copy.deepcopy(self.exp_params),
        }
        return self

    def load_profile(self, name: str):
        """
        Load a previously saved profile and overwrite current config.
        Raises KeyError if profile does not exist.
        """
        prof = self._profiles[name]  # let KeyError surface if missing
        self.script = prof["script"]
        self.command = prof["command"]
        self.workdir = prof["workdir"]
        self.exp_params = copy.deepcopy(prof["params"])
        return self  # allow chaining

    def delete_profile(self, name: str):
        """
        Remove a profile if it exists.
        """
        self._profiles.pop(name, None)
        return self  # allow chaining

    def list_profiles(self):
        """
        Return a list of saved profile names.
        """
        return list(self._profiles.keys())

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _construct_args(self):
        args = [self.command, "-q", self.script]
        for key, value in self.exp_params.items():
            args.append(f"{key}={repr(value)}")
        return args

    def _extract_timestamps(self, stdout: str, stderr: str = None) -> str:
        combined = (stdout or "") + "\n" + (stderr or "")
        m = re.search(r"(\d{8}_\d{6})", combined)
        return m.group(1) if m else ""

    def _clean_output(self, cp):
        """
        Remove big chunk of datasets from stdout
        Blacklist based, if not on list it would be kept
        depends on drop_keys in config.py
        """

        stdout = cp.stdout
        key_re = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*')

        out_lines = []
        dropping_big_block = False

        for line in stdout.splitlines(True):  # keep newline
            m = key_re.match(line)
            if m:
                key = m.group(1)
                rest = line[m.end():].lstrip()
                if key in drop_keys and rest.startswith("["):
                    if key == "arr_of_timestamps":
                        dropping_big_block = True
                    continue

            if dropping_big_block:
                if (line.strip() == "") or key_re.match(line):
                    dropping_big_block = False
                else:
                    continue

            out_lines.append(line)

        return "".join(out_lines), cp.stderr

    def _write_log(self, timestamp: str, stdout: str, stderr: str):

        try:
            date, time = timestamp.split("_")
        except Exception:
            date, time = self._last_run_time.split("_")

        os.makedirs(f"{self.log_path}/{date}", exist_ok=True)

        log_file = f"{self.log_path}/{date}/output_log.txt"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"timestamp: {timestamp}\n")
            f.write("stdout:\n" + stdout + "\n\n")
            f.write("stderr:\n" + stderr + "\n")
            f.write("=" * 60 + "\n")

    # -----------------------------
    # Main Utilities
    # -----------------------------
    def print_args(self):
        print(self._construct_args())

    def run(self) -> str:

        self._last_run_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        cp = subprocess.run(
            self._construct_args(),
            capture_output=True,
            text=True,
            cwd = self.workdir
        )

        stdout, stderr = self._clean_output(cp)
        self.last_output = (stdout, stderr)
        timestamp = self._extract_timestamps(stdout, stderr)
        self._write_log(timestamp, stdout, stderr)

        return timestamp

# 2) Subclass for single_parameter_scan
# =============================================================================
class SingleParameterScan(ArtiqController):
    """
    Convenience wrapper for single_parameter_scan.py (OFAT scan).
    """

    def __init__(
            self,
            command: str = "artiq_run",
            script_path: str = "/home/electrons/software/Electrons_Artiq_Sequences/"
                               "artiq-master/repository/Modular/single_parameter_scan.py"
        ):
        super().__init__(script_path=script_path, command=command)

    def run(
        self,
        *,
        # Common “sequence settings”
        mode: str = "Trapping",
        # OFAT scan settings
        scanning_parameter: str = "tickle_frequency",
        min_scan: float = 1.0,
        max_scan: float = 150.0,
        steps: int = 150,
        # Allow any additional ARTIQ parameters to be passed through
        **extra_params,
    ) -> str:
        """
        Run single_parameter_scan with the most-used knobs as named args.

        Explicit parameters here:
        - mode
        - scanning_parameter, min_scan, max_scan, steps

        Any additional ARTIQ parameters (Ex, RF_on, etc.) via **extra_params.
        """

        self.load_params({
            "mode": mode,
            "scanning_parameter": scanning_parameter,
            "min_scan": min_scan,
            "max_scan": max_scan,
            "steps": steps,
        })
        # Pass everything else through (e.g. U1, Ex, Ey, tickle_level, etc.)
        self.load_params(extra_params)

        return super().run()

# 3) Subclass for doe_scan
# =============================================================================
class DoeScan(ArtiqController):
    """
    Convenience wrapper for doe_scan.py (DOE scan).
    """

    def __init__(
            self,
            command: str = "artiq_run",
            script_path: str = "/home/electrons/software/Electrons_Artiq_Sequences/"
                               "artiq-master/repository/Modular/doe_scan.py"
        ):
        super().__init__(script_path=script_path, command=command)

    def run(
        self,
        *,
        # common "sequence settings"
        mode: str = "Trapping",
        utility_mode: str = "DOE Scan",
        # DOE scan settings
        doe_file_path: str = "/home/electrons/software/"
                             "Electrons_Artiq_Sequences/artiq-master/doe_configs/",
        doe_file_name: str = "doe_table.csv",
        **extra_params,
    ) -> str:
        """
        Run doe_scan.py with the main DOE knobs as named args.

        Explicit parameters here:
        - mode, utility_mode
        - doe_file_path, doe_file_name

        Any additional ARTIQ parameters (Ex, RF_on, etc.) via **extra_params.
        """
        self.load_params({
            "mode": mode,
            "utility_mode": utility_mode,
            "doe_file_path": doe_file_path,
            "doe_file_name": doe_file_name,
        })
        self.load_params(extra_params)
        return super().run()

# 4) Subclass for find_optimal_E
# =============================================================================
class FindOptimalE(ArtiqController):
    """
    Convenience wrapper for find_optimal_E.py (Bayesian Optimizer).
    """

    def __init__(
            self,
            command: str = "artiq_run",
            script_path: str = "/home/electrons/software/Electrons_Artiq_Sequences/"
                               "artiq-master/repository/Modular/find_optimal_E.py"
        ):
        super().__init__(script_path=script_path, command=command)

    @staticmethod
    def _parse_optimal_Es(stdout: str, stderr: str = None):
        """
        Parse the two 'E = [...]' lines printed by printout_final_result(self).

        Returns:
            (E_best_obs, E_best_model), each a 3-tuple of floats,
            or (None, None) if parsing fails.
        """
        combined = (stdout or "") + "\n" + (stderr or "")
        matches = re.findall(r"E\s*=\s*\[([^\]]+)\]", combined)
        if len(matches) < 2:
            return None, None

        def parse_vec(s: str):
            parts = s.split(",")
            return tuple(float(p.strip()) for p in parts)

        E_best_obs = parse_vec(matches[0])
        E_best_model = parse_vec(matches[1])
        return E_best_obs, E_best_model

    def run(
        self,
        *,
        optimize_target: str = "ratio_signal",
        max_iteration: int = 50,
        tolerance: float = 5e-3,
        converge_count: int = 3,
        min_Ex: float = -0.25,
        max_Ex: float = 0.05,
        min_Ey: float = -0.05,
        max_Ey: float = 0.20,
        min_Ez: float = -0.10,
        max_Ez: float = 0.10,
        no_of_repeats: int = 3000,
        get_output = False,
        **extra_params,
    ):
        # Set parameters
        self.load_params({
            "optimize_target": optimize_target,
            "max_iteration": max_iteration,
            "tolerance": tolerance,
            "converge_count": converge_count,
            "min_Ex": min_Ex,
            "max_Ex": max_Ex,
            "min_Ey": min_Ey,
            "max_Ey": max_Ey,
            "min_Ez": min_Ez,
            "max_Ez": max_Ez,
            "no_of_repeats": no_of_repeats,
        })
        self.load_params(extra_params)

        # Run ARTIQ and capture stdout
        cp = subprocess.run(
            self._construct_args(),
            capture_output=True,
            text=True,
            cwd = self.workdir
        )

        # Parse both E's and timestamp from the printed analyze output
        E_best_obs, E_best_model = self._parse_optimal_Es(cp.stdout, cp.stderr)
        timestamp = self._extract_timestamps(cp.stdout, cp.stderr)

        if get_output:
            return E_best_obs, E_best_model, timestamp, (cp.stdout, cp.stderr)
        else:
            return E_best_obs, E_best_model, timestamp

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
