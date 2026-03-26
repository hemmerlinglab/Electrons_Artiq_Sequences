import subprocess
import copy
import re
from datetime import datetime
import json
import traceback
import threading
import queue
import os

from config import drop_keys

# 0) Helper Functions
# =============================================================================
def timestamp_string():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# 1) Master Class
# =============================================================================
class ArtiqController:

    def __init__(
            self,
            script_path: str = None,
            command: str = "artiq_run",
            workdir: str = "/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/",
            log_path: str = "/home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/result",
            comment: str = ""
        ):

        # Attributes
        self.exp_params = {}
        self.command = command
        self.script = script_path
        self.workdir = workdir    # Must set appropriately otherwise artiq would crash
        self.log_path = log_path
        self.last_output = ("", "")
        self.live_status = {
            "laser_off_422": False,
            "laser_off_390": False,
        }

        # Private Attributes
        self._profiles = {}       # In-memory profiles: name -> {"script": ..., "command": ..., "params": {...}}
        self._creation_time = timestamp_string()
        self._creation_date = self._creation_time.split("_")[0]
        self._instance_log = os.path.join(self.log_path, self._creation_date, f"{self._creation_time}.json")
        self._instance_log_initialized = False

        # Ensure save dirs
        os.makedirs(self.log_path, exist_ok=True)
        os.makedirs(os.path.join(self.log_path, self._creation_date), exist_ok=True)
        self._write_initial_instance_log(comment)

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
    # 1. parse IO with system terminal and artiq
    # +++++++++++++++++++++++++++++++++++++++++++++++++
    def _construct_args(self):
        args = [self.command, "-q", self.script]
        for key, value in self.exp_params.items():
            args.append(f"{key}={repr(value)}")
        return args

    def _extract_timestamps(self, stdout: str, stderr: str = None) -> str:
        combined = (stdout or "") + "\n" + (stderr or "")
        m = re.search(r"(\d{8}_\d{6})", combined)
        return m.group(1) if m else ""

    # 2. logging utilities
    # +++++++++++++++++++++++++++++++++++++++++++++++++
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

    def _write_output_log(
        self,
        timestamp: str,
        stdout: str,
        stderr: str,
        controller_traceback: str = "",
        returncode = None,
    ):

        try:
            date, time = timestamp.split("_")
        except Exception:
            date, time = self._last_run_time.split("_")

        os.makedirs(f"{self.log_path}/{date}", exist_ok=True)

        log_file = f"{self.log_path}/{date}/output_log.txt"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"timestamp: {timestamp}\n")
            if returncode is not None:
                f.write(f"returncode: {returncode}\n")
            f.write("stdout:\n" + stdout + "\n\n")
            f.write("stderr:\n" + stderr + "\n")
            if controller_traceback:
                f.write("\ncontroller_traceback:\n" + controller_traceback + "\n")
            f.write("=" * 60 + "\n")

    def _write_initial_instance_log(self, comment: str):
        """
        Write the instance log file with metadata header (once per instance).
        Creates a beautiful, human-readable JSON structure.
        """
        metadata = {
            "experiment_comment": comment,
            "command": self.command,
            "script": self.script,
            "workdir": self.workdir,
            "log_path": self.log_path,
        }
        doc = {
            "metadata": metadata,
            "runs": [],
        }
        with open(self._instance_log, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        self._instance_log_initialized = True

    def _write_instance_log(self, timestamp: str):
        """
        Append a run entry to the instance log.
        Maintains a beautiful, readable JSON structure.
        Includes exp_params (run parameters) in each run entry.
        """
        run_entry = {
            "experiment_timestamp": timestamp if timestamp else self._last_run_time,
            "started_at": self._last_run_time,
            "ended_at": self._last_end_time,
            "params": copy.deepcopy(self.exp_params),
        }
        with open(self._instance_log, "r", encoding="utf-8") as f:
            doc = json.load(f)
        doc["runs"].append(run_entry)
        with open(self._instance_log, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

    # 3. monitor artiq status in real time
    # +++++++++++++++++++++++++++++++++++++++++++++++++
    def _reset_live_status(self):
        self.live_status = {
            "laser_off_422": False,
            "laser_off_390": False,
        }

    def _handle_live_stdout_line(self, line: str):
        """
        Set the status you require the ArtiqController class to monitor
        currently monitoring laser errors for 390 and 422
        """
        if "STATUS:LASER_OFF_422" in line:
            self.live_status["laser_off_422"] = True
            print("[ArtiqController] Laser 422 needs manual fix.")

        if "STATUS:LASER_OFF_390" in line:
            self.live_status["laser_off_390"] = True
            print("[ArtiqController] Laser 390 needs manual fix.")

    def _spawn_process(self):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        return subprocess.Popen(
            self._construct_args(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.workdir,
            env=env,
        )

    def _start_stream_reader_threads(self, proc, q):

        def reader(pipe, tag):
            try:
                for line in iter(pipe.readline, ''):
                    q.put((tag, line))
            finally:
                pipe.close()

        t_out = threading.Thread(target=reader, args=(proc.stdout, "stdout"), daemon=True)
        t_err = threading.Thread(target=reader, args=(proc.stderr, "stderr"), daemon=True)
        t_out.start()
        t_err.start()

        return t_out, t_err

    def _collect_stream_output(self, proc, q, stdout_lines, stderr_lines):

        while True:
            try:
                tag, line = q.get(timeout=0.1)
            except queue.Empty:
                if proc.poll() is not None:
                    if q.empty():
                        break
                    continue
                continue

            if tag == "stdout":
                stdout_lines.append(line)
                self._handle_live_stdout_line(line)
            else:
                stderr_lines.append(line)

    def _finalize_completed_process(self, proc, returncode, stdout_lines, stderr_lines):
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        cp = subprocess.CompletedProcess(proc.args, returncode, stdout, stderr)
        stdout, stderr = self._clean_output(cp)
        self.last_output = (stdout, stderr)
        timestamp = self._extract_timestamps(stdout, stderr)

        return stdout, stderr, timestamp

    # -----------------------------
    # Main Utilities
    # -----------------------------
    def run(self) -> str:

        proc = None
        stdout = ""
        stderr = ""
        stdout_lines = []
        stderr_lines = []
        timestamp = ""
        controller_traceback = ""
        returncode = None
        q = queue.Queue()

        # run experiment with real-time monitoring on Artiq's output
        try:
            self._last_run_time = timestamp_string()
            self._reset_live_status()

            proc = self._spawn_process()
            self._start_stream_reader_threads(proc, q)
            self._collect_stream_output(proc, q, stdout_lines, stderr_lines)

            returncode = proc.wait()
            stdout, stderr, timestamp = self._finalize_completed_process(
                proc, returncode, stdout_lines, stderr_lines
            )

            return timestamp

        # if the operator do KeyboardInterrupt, keep traceback and crash
        except BaseException:
            controller_traceback = traceback.format_exc()
            raise

        # no matter the process succeeded or failed, write log
        finally:
            self._last_end_time = timestamp_string()
            self._write_output_log(
                timestamp,
                stdout if stdout else "".join(stdout_lines),
                stderr if stderr else "".join(stderr_lines),
                controller_traceback=controller_traceback,
                returncode=returncode,
            )
            self._write_instance_log(timestamp)

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
                               "artiq-master/repository/Modular/single_parameter_scan.py",
            comment: str = "",
        ):
        super().__init__(script_path=script_path, command=command, comment=comment)

    def run(
        self,
        *,
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

    def _write_instance_log(
        self, timestamp: str, E_best_obs: tuple = None, E_best_model: tuple = None
    ):
        """
        Override: append a run entry including exp_params, E_best_obs and E_best_model.
        """
        run_entry = {
            "experiment_timestamp": timestamp,
            "started_at": self._last_run_time,
            "ended_at": timestamp,
            "params": copy.deepcopy(self.exp_params),
        }
        if E_best_obs is not None:
            run_entry["E_best_obs"] = list(E_best_obs)
        if E_best_model is not None:
            run_entry["E_best_model"] = list(E_best_model)
        with open(self._instance_log, "r", encoding="utf-8") as f:
            doc = json.load(f)
        doc["runs"].append(run_entry)
        with open(self._instance_log, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

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
        **extra_params,
    ):
        proc = None
        stdout = ""
        stderr = ""
        stdout_lines = []
        stderr_lines = []
        timestamp = ""
        controller_traceback = ""
        returncode = None
        E_best_obs = None
        E_best_model = None
        q = queue.Queue()

        # run experiment with real-time monitoring on Artiq's output
        try:
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

            self._last_run_time = timestamp_string()
            self._reset_live_status()

            proc = self._spawn_process()
            self._start_stream_reader_threads(proc, q)
            self._collect_stream_output(proc, q, stdout_lines, stderr_lines)

            returncode = proc.wait()
            stdout, stderr, timestamp = self._finalize_completed_process(
                proc, returncode, stdout_lines, stderr_lines
            )

            E_best_obs, E_best_model = self._parse_optimal_Es(stdout, stderr)

            return E_best_obs, E_best_model, timestamp

        # if the operator do KeyboardInterrupt, keep traceback and crash
        except BaseException:
            controller_traceback = traceback.format_exc()
            raise

        # no matter the process succeeded or failed, write log
        finally:
            self._last_end_time = timestamp_string()
            self._write_output_log(
                timestamp,
                stdout if stdout else "".join(stdout_lines),
                stderr if stderr else "".join(stderr_lines),
                controller_traceback=controller_traceback,
                returncode=returncode,
            )
            self._write_instance_log(timestamp, E_best_obs, E_best_model)


if __name__ == "__main__":
    ac = (
        ArtiqController("MCP_PowerSupply.py")
        .set_param("mode", "custom")
        .set_param("front", 200)
        .set_param("back", 2200)
        .set_param("anode", 2400)
    )
    ac.print_args()

    """
    cmd = 'artiq_run -q ../Electrons/Scan_DC_electrodes.py time_count=' + str(time_count) + ' mesh_voltage=' + str(mesh_voltage) + ' Zotino_channel=' + str(elec_dict[e]) + ' minimum=' + str(min_volt) + ' maximum=' + str(max_volt) + ' steps=' + str(steps)
    """
