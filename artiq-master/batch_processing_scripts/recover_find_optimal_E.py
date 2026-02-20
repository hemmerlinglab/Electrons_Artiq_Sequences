#!/usr/bin/env python3
"""
Recover FindOptimalE scan results after a crash by combining:
1) *_conf files in /home/electrons/software/data/<DATE>/ to get U2 + RF_amplitude (and filter)
2) output_log.txt (your ArtiqController log) to get Best observed/model E for each timestamp
3) (optional) per-run performance signals from data files (loading_signal, ratio_signal, ...)

Outputs:
- per_run.csv (one row per timestamp)
- per_u2_agg.csv (trimmed mean/std over repeats for each U2)
- scan_observed.png, scan_model.png (3 stacked subplots Ex/Ey/Ez vs U2)
- scan_signals_2x3.png (5 signals + 1 empty)

Example:
  python recover_find_optimal_E.py --date 20260220 --after 020000 --rf 2.5 \\
    --out-log /home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/result/20260220/output_log.txt \\
    --out-dir /home/electrons/software/Electrons_Artiq_Sequences/artiq-master/batch_processing_scripts/result/20260220
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Tuple, Optional, List

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# -----------------------------
# Parsing helpers
# -----------------------------
_TS_RE = re.compile(r"timestamp:\s*(\d{8}_\d{6})")
_OBS_RE = re.compile(
    r"Best observed \(incumbent\):\s*[\r\n]+\s*value\s*=\s*([0-9eE\.\+\-]+)\s*[\r\n]+\s*E\s*=\s*\[([^\]]+)\]",
    re.MULTILINE,
)
_MOD_RE = re.compile(
    r"Best predicted by GP.*?:\s*[\r\n]+\s*mean\s*=\s*([0-9eE\.\+\-]+)\s*[\r\n]+\s*E\s*=\s*\[([^\]]+)\]",
    re.MULTILINE,
)


def _parse_vec(s: str) -> Tuple[float, float, float]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) < 3:
        raise ValueError(f"Bad vector string: {s}")
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def parse_output_log(path: Path) -> Dict[str, dict]:
    """
    Returns mapping:
      ts -> {
        obs_value, obs_Ex, obs_Ey, obs_Ez,
        model_mean, model_Ex, model_Ey, model_Ez
      }
    """
    txt = path.read_text(encoding="utf-8", errors="replace")

    # Split blocks on your delimiter line (60 '=')
    blocks = re.split(r"\n=+\n", txt)
    out: Dict[str, dict] = {}

    for b in blocks:
        m_ts = _TS_RE.search(b)
        if not m_ts:
            continue
        ts = m_ts.group(1)

        d: dict = {}
        m_obs = _OBS_RE.search(b)
        if m_obs:
            d["obs_value"] = float(m_obs.group(1))
            ex, ey, ez = _parse_vec(m_obs.group(2))
            d["obs_Ex"], d["obs_Ey"], d["obs_Ez"] = ex, ey, ez

        m_mod = _MOD_RE.search(b)
        if m_mod:
            d["model_mean"] = float(m_mod.group(1))
            ex, ey, ez = _parse_vec(m_mod.group(2))
            d["model_Ex"], d["model_Ey"], d["model_Ez"] = ex, ey, ez

        out[ts] = d

    return out


def parse_conf_file(path: Path) -> Dict[str, str]:
    """
    Parses your *_conf format into {key: val_string}.
    Only grabs the 'val =' line under each [section].
    """
    cur = None
    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = line.strip("[]").strip()
            continue
        if cur and line.startswith("val ="):
            out[cur] = line.split("=", 1)[1].strip()
    return out


def safe_float(x: str) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def trimmed_mean_std(arr: np.ndarray, trim_pct: float = 0.1, trim_min: int = 1) -> Tuple[float, float]:
    arr = np.asarray(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n == 0:
        return (np.nan, np.nan)
    if n < 3:
        return (float(np.mean(arr)), float(np.std(arr)))

    trim = int(max(n * trim_pct, trim_min))
    trim = min(trim, (n - 1) // 2)
    if trim <= 0:
        return (float(np.mean(arr)), float(np.std(arr)))

    s = np.sort(arr)
    s2 = s[trim:-trim]
    if s2.size == 0:
        return (float(np.mean(arr)), float(np.std(arr)))
    return (float(np.mean(s2)), float(np.std(s2)))


# -----------------------------
# Data loading (signals)
# -----------------------------
def load_1d_dataset(data_dir: Path, date: str, ts: str, name: str) -> np.ndarray:
    p = data_dir / date / f"{ts}_{name}"
    return np.genfromtxt(str(p), delimiter=",")  # delimiter ok even if none


def signal_summary(arr: np.ndarray) -> float:
    # match your earlier logic: per-run performance as nanmax
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return float("nan")
    return float(np.nanmax(arr))


# -----------------------------
# Plotting
# -----------------------------
def plot_E_3x1(x: List[float], means: dict, stds: dict, title: str, x_label: str, out_png: Path):
    comps = ["Ex", "Ey", "Ez"]
    ylabels = ["Optimal Ex [V/m]", "Optimal Ey [V/m]", "Optimal Ez [V/m]"]

    fig, axes = plt.subplots(3, 1, figsize=(8, 12), sharex=True)
    for ax, comp, yl in zip(axes, comps, ylabels):
        ax.errorbar(x, means[comp], yerr=stds[comp], fmt="-o", capsize=4)
        ax.set_ylabel(yl)
        ax.grid(True, alpha=0.3)

    axes[0].set_title(title)
    axes[-1].set_xlabel(x_label)
    plt.tight_layout()
    fig.savefig(out_png, dpi=300)
    plt.close(fig)
    print(f"[Save] {out_png}")


def plot_signals_2x3(x: List[float], means: dict, stds: dict, signals: List[str], x_label: str, title: str, out_png: Path):
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
    axes = axes.ravel()

    for i, s in enumerate(signals):
        ax = axes[i]
        ax.errorbar(x, means[s], yerr=stds[s], fmt="-o", capsize=4)
        ax.set_title(s)
        ax.grid(True, alpha=0.3)

    axes[len(signals)].axis("off")

    for ax in axes[3:5]:
        ax.set_xlabel(x_label)

    fig.suptitle(title, fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_png, dpi=300)
    plt.close(fig)
    print(f"[Save] {out_png}")


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYYMMDD, e.g. 20260220")
    ap.add_argument("--after", default="020000", help="HHMMSS threshold inside that date (string compare), default 020000")
    ap.add_argument("--rf", type=float, default=2.5, help="RF_amplitude setpoint to filter, default 2.5")
    ap.add_argument("--rf-tol", type=float, default=1e-6, help="tolerance on RF_amplitude match")
    ap.add_argument("--data-dir", default="/home/electrons/software/data", help="base data dir")
    ap.add_argument("--out-log", required=True, help="path to output_log.txt")
    ap.add_argument("--out-dir", required=True, help="where to write outputs (will make date subdir if you pass parent)")
    ap.add_argument("--no-signals", action="store_true", help="skip loading performance signals (faster)")
    args = ap.parse_args()

    date = args.date
    ts_min = f"{date}_{args.after}"

    data_dir = Path(args.data_dir)
    out_log = Path(args.out_log)
    out_dir = Path(args.out_dir)

    # If user passed parent folder, keep outputs under out_dir/date
    if out_dir.name != date:
        out_dir = out_dir / date
    out_dir.mkdir(parents=True, exist_ok=True)

    log_map = parse_output_log(out_log)
    print(f"[Info] Parsed {len(log_map)} timestamps from output_log")

    # Find conf files for that date
    conf_dir = data_dir / date
    conf_files = sorted(conf_dir.glob(f"{date}_*_conf"))
    print(f"[Info] Found {len(conf_files)} *_conf files in {conf_dir}")

    SIGNALS = ["loading_signal", "trapped_signal", "lost_signal", "ratio_signal", "ratio_lost"]

    per_run_rows = []
    for cf in conf_files:
        ts = cf.name.replace("_conf", "")
        if ts < ts_min:
            continue

        conf = parse_conf_file(cf)
        rf = safe_float(conf.get("RF_amplitude", "nan"))
        if not np.isfinite(rf) or abs(rf - args.rf) > args.rf_tol:
            continue

        u2 = safe_float(conf.get("U2", "nan"))
        if not np.isfinite(u2):
            continue

        if ts not in log_map:
            # possible if crash happened before log write
            continue

        row = {
            "timestamp": ts,
            "U2": float(u2),
            "RF_amplitude": float(rf),
        }
        row.update(log_map[ts])

        if not args.no_signals:
            for s in SIGNALS:
                try:
                    arr = load_1d_dataset(data_dir, date, ts, s)
                    row[s] = signal_summary(arr)
                except Exception:
                    row[s] = float("nan")

        per_run_rows.append(row)

    if not per_run_rows:
        raise SystemExit("No matching runs found. Check --date/--after/--rf and paths.")

    # Save per-run CSV
    per_run_csv = out_dir / "recovered_per_run.csv"
    fieldnames = sorted({k for r in per_run_rows for k in r.keys()})
    with open(per_run_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(per_run_rows)
    print(f"[Save] {per_run_csv} ({len(per_run_rows)} rows)")

    # Aggregate by U2
    u2_vals = sorted({r["U2"] for r in per_run_rows})
    agg = {
        "U2": [],
        "Observed": {"Ex": [], "Ey": [], "Ez": [], "value": []},
        "Observed_std": {"Ex": [], "Ey": [], "Ez": [], "value": []},
        "Model": {"Ex": [], "Ey": [], "Ez": [], "mean": []},
        "Model_std": {"Ex": [], "Ey": [], "Ez": [], "mean": []},
        "Signals": {s: [] for s in SIGNALS},
        "Signals_std": {s: [] for s in SIGNALS},
    }

    def collect(u2: float, key: str) -> np.ndarray:
        return np.array([r.get(key, np.nan) for r in per_run_rows if r["U2"] == u2], dtype=float)

    for u2 in u2_vals:
        agg["U2"].append(u2)

        # observed
        for comp_key, out_key in [("obs_Ex","Ex"),("obs_Ey","Ey"),("obs_Ez","Ez"),("obs_value","value")]:
            mu, sd = trimmed_mean_std(collect(u2, comp_key))
            agg["Observed"][out_key].append(mu)
            agg["Observed_std"][out_key].append(sd)

        # model
        for comp_key, out_key in [("model_Ex","Ex"),("model_Ey","Ey"),("model_Ez","Ez"),("model_mean","mean")]:
            mu, sd = trimmed_mean_std(collect(u2, comp_key))
            agg["Model"][out_key].append(mu)
            agg["Model_std"][out_key].append(sd)

        if not args.no_signals:
            for s in SIGNALS:
                mu, sd = trimmed_mean_std(collect(u2, s))
                agg["Signals"][s].append(mu)
                agg["Signals_std"][s].append(sd)

    # Save aggregated CSV
    agg_csv = out_dir / "recovered_per_u2_agg.csv"
    rows = []
    for i, u2 in enumerate(agg["U2"]):
        r = {
            "U2": u2,
            "obs_Ex": agg["Observed"]["Ex"][i], "obs_Ex_std": agg["Observed_std"]["Ex"][i],
            "obs_Ey": agg["Observed"]["Ey"][i], "obs_Ey_std": agg["Observed_std"]["Ey"][i],
            "obs_Ez": agg["Observed"]["Ez"][i], "obs_Ez_std": agg["Observed_std"]["Ez"][i],
            "obs_value": agg["Observed"]["value"][i], "obs_value_std": agg["Observed_std"]["value"][i],
            "model_Ex": agg["Model"]["Ex"][i], "model_Ex_std": agg["Model_std"]["Ex"][i],
            "model_Ey": agg["Model"]["Ey"][i], "model_Ey_std": agg["Model_std"]["Ey"][i],
            "model_Ez": agg["Model"]["Ez"][i], "model_Ez_std": agg["Model_std"]["Ez"][i],
            "model_mean": agg["Model"]["mean"][i], "model_mean_std": agg["Model_std"]["mean"][i],
        }
        if not args.no_signals:
            for s in SIGNALS:
                r[s] = agg["Signals"][s][i]
                r[s + "_std"] = agg["Signals_std"][s][i]
        rows.append(r)

    with open(agg_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"[Save] {agg_csv} ({len(rows)} U2 points)")

    # Plots
    x = agg["U2"]
    plot_E_3x1(
        x,
        {"Ex": agg["Observed"]["Ex"], "Ey": agg["Observed"]["Ey"], "Ez": agg["Observed"]["Ez"]},
        {"Ex": agg["Observed_std"]["Ex"], "Ey": agg["Observed_std"]["Ey"], "Ez": agg["Observed_std"]["Ez"]},
        title=f"FindOptimalE (Observed) vs U2  | RF_amplitude={args.rf} | after {args.after}",
        x_label="U2",
        out_png=out_dir / "recovered_scan_observed.png",
    )
    plot_E_3x1(
        x,
        {"Ex": agg["Model"]["Ex"], "Ey": agg["Model"]["Ey"], "Ez": agg["Model"]["Ez"]},
        {"Ex": agg["Model_std"]["Ex"], "Ey": agg["Model_std"]["Ey"], "Ez": agg["Model_std"]["Ez"]},
        title=f"FindOptimalE (Model) vs U2  | RF_amplitude={args.rf} | after {args.after}",
        x_label="U2",
        out_png=out_dir / "recovered_scan_model.png",
    )

    if not args.no_signals:
        plot_signals_2x3(
            x,
            agg["Signals"],
            agg["Signals_std"],
            SIGNALS,
            x_label="U2",
            title=f"Signals vs U2 | RF_amplitude={args.rf} | after {args.after}",
            out_png=out_dir / "recovered_scan_signals_2x3.png",
        )

    # Save a small JSON metadata too
    meta = {
        "date": date,
        "after": args.after,
        "rf_filter": args.rf,
        "n_runs": len(per_run_rows),
        "n_u2": len(u2_vals),
        "out_log": str(out_log),
    }
    (out_dir / "recovered_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("[Done] Recovery complete.")


if __name__ == "__main__":
    main()
