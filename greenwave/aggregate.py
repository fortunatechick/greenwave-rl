"""Turn per-episode evaluation rows into the tables behind the report and the website.

An RL "family" is a training configuration (e.g. ddqn_fair__peak); its jobs are the
training seeds. For every evaluation seed the metrics of a family are averaged over its
training seeds, and mean / std / Welch tests are then taken over the evaluation seeds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from greenwave.config import CLASSES, REGIMES, ROOT
from greenwave.metrics import LOWER_IS_BETTER, MAIN_METRICS, welch_p

SUMMARY = ROOT / "results" / "summary"
WAITS = ROOT / "results" / "raw" / "waits"

ID_COLS = ("controller", "regime", "seed")
TABLE_METRICS = [
    *MAIN_METRICS,
    *[f"delay_{c}" for c in CLASSES],
    *[f"wait_{c}" for c in CLASSES],
    "forced_switches", "teleports", "depart_delay", "switches",
]  # fmt: skip

# Display rows of the main table -> training family for a given test regime.
RL_ROWS = {
    "ddqn_fair": lambda regime: f"ddqn_fair__{regime}",
    "ddqn_fair_dr": lambda regime: "ddqn_fair__dr",
    "dqn_sb3": lambda regime: "dqn_sb3__peak",
    "ppo": lambda regime: "ppo__peak",
}
CONTROLLER_LABELS = {
    "fixed_matched": "Fixed-time (matched plan)",
    "fixed_peak": "Fixed-time (stale peak plan)",
    "actuated": "Actuated",
    "max_pressure": "Max-pressure",
    "random": "Random phase",
    "ddqn_fair": "Double DQN, fair reward (ours)",
    "ddqn_fair_dr": "Double DQN, fair + DR (ours)",
    "dqn_sb3": "DQN, SB3 (trained on peak)",
    "ppo": "PPO, SB3 (trained on peak)",
}

# Ablation groups: (regime, [(family, variant label, is_reference)]).
ABLATION_GROUPS: dict[str, tuple[str, list[tuple[str, str, bool]]]] = {
    "reward": ("peak", [
        ("abl_ref__peak", "ours (passenger + fairness)", True),
        ("abl_reward_wait__peak", "waiting time", False),
        ("abl_reward_queue__peak", "queue length", False),
        ("abl_reward_pressure__peak", "pressure", False),
    ]),
    "fairness": ("skewed", [
        ("abl_ref__skewed", "with fairness penalty", True),
        ("abl_nofair__skewed", "no penalty (lambda = 0)", False),
    ]),
    "weighting": ("peak", [
        ("abl_ref__peak", "passenger-weighted", True),
        ("abl_vehicle_fair__peak", "vehicle-count", False),
    ]),
    "bus_weight": ("peak", [
        ("abl_bus20__peak", "bus = 20", False),
        ("abl_ref__peak", "bus = 40", True),
        ("abl_bus60__peak", "bus = 60", False),
    ]),
    "state": ("peak", [
        ("abl_ref__peak", "full state", True),
        ("abl_notimer__peak", "no phase timer", False),
        ("abl_nomaxwait__peak", "no max-wait feature", False),
    ]),
    "interval": ("peak", [
        ("abl_ref__peak", "5 s", True),
        ("abl_delta10__peak", "10 s", False),
        ("abl_delta15__peak", "15 s", False),
    ]),
    "sublane": ("peak", [
        ("abl_ref__peak", "agent, sub-lane on", True),
        ("abl_nosublane__peak", "agent, sub-lane off", False),
    ]),
}  # fmt: skip
ABLATION_METRICS = ["person_wait", "veh_wait", "max_wait", "wait_p95", "delay_bus", "delay_car"]


def family_of(job: str) -> str:
    return job.rsplit("__s", 1)[0]


def read_episodes(tag: str) -> pd.DataFrame:
    path = SUMMARY / f"episodes_{tag}.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=list(ID_COLS))


def metric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in TABLE_METRICS if c in df.columns]


def family_episodes(agents: pd.DataFrame) -> pd.DataFrame:
    """One row per (family, regime, eval seed): metrics averaged over training seeds."""
    if agents.empty:
        return pd.DataFrame(columns=["family", "regime", "seed", "n_train"])
    df = agents.copy()
    df["family"] = df["controller"].map(family_of)
    cols = metric_columns(df)
    out = df.groupby(["family", "regime", "seed"], as_index=False)[cols].mean()
    n_train = df.groupby(["family", "regime", "seed"])["controller"].nunique().reset_index(name="n_train")
    return out.merge(n_train, on=["family", "regime", "seed"])


def series(df: pd.DataFrame, key_col: str, key: str, regime: str, metric: str) -> np.ndarray:
    if df.empty or metric not in df.columns:
        return np.array([])
    sel = df[(df[key_col] == key) & (df["regime"] == regime)].sort_values("seed")
    values = sel[metric].to_numpy(dtype=float)
    return values[np.isfinite(values)]


def stat_row(values: np.ndarray) -> dict[str, float] | None:
    if len(values) == 0:
        return None
    return {"mean": float(values.mean()), "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            "n": int(len(values))}  # fmt: skip


def clean_p(p: float) -> float | None:
    return None if not np.isfinite(p) else float(p)


def main_rows(base: pd.DataFrame, fam: pd.DataFrame) -> list[dict[str, Any]]:
    """Every controller in every regime for every metric, with Welch p-values."""
    rows: list[dict[str, Any]] = []
    metrics = metric_columns(base)
    baselines = [c for c in CONTROLLER_LABELS if c in set(base["controller"])]
    for regime in REGIMES:
        for metric in metrics:
            fixed = series(base, "controller", "fixed_matched", regime, metric)
            mp = series(base, "controller", "max_pressure", regime, metric)
            entries = [(c, series(base, "controller", c, regime, metric)) for c in baselines]
            entries += [(k, series(fam, "family", f(regime), regime, metric)) for k, f in RL_ROWS.items()]
            for key, values in entries:
                stats = stat_row(values)
                if stats is None:
                    continue
                rows.append({
                    "regime": regime, "controller": key, "metric": metric, **stats,
                    "p_vs_fixed": None if key == "fixed_matched" else clean_p(welch_p(values, fixed)),
                    "p_vs_mp": None if key == "max_pressure" else clean_p(welch_p(values, mp)),
                })  # fmt: skip
    return rows


def generalisation(fam: pd.DataFrame, metric: str) -> dict[str, Any] | None:
    """Rows: trained on regime A. Columns: tested on regime B. Plus the DR row."""
    regimes = list(REGIMES)
    matrix, std = [], []
    for a in regimes:
        row, srow = [], []
        for b in regimes:
            stats = stat_row(series(fam, "family", f"ddqn_fair__{a}", b, metric))
            if stats is None:
                return None
            row.append(stats["mean"])
            srow.append(stats["std"])
        matrix.append(row)
        std.append(srow)
    dr = [stat_row(series(fam, "family", "ddqn_fair__dr", b, metric)) for b in regimes]
    dr_row = [s["mean"] for s in dr if s]
    dr_std = [s["std"] for s in dr if s]
    m = np.asarray(matrix)
    diagonal = float(np.mean(np.diag(m)))
    off = float((m.sum() - np.trace(m)) / (m.size - len(regimes)))
    gap = None
    if len(dr_row) == len(regimes) and abs(off - diagonal) > 1e-9:
        gap = 100.0 * (off - float(np.mean(dr_row))) / (off - diagonal)
    return {"metric": metric, "regimes": regimes, "matrix": matrix, "std": std,
            "dr_row": dr_row if len(dr_row) == len(regimes) else [], "dr_std": dr_std,
            "gap_recovered_pct": gap, "diagonal_mean": diagonal, "off_diagonal_mean": off}  # fmt: skip


def pct(new: float, old: float) -> float:
    return 100.0 * (new - old) / old if old else float("nan")


def sig(p: float | None) -> str:
    if p is None or not np.isfinite(p):
        return "significance not testable"
    return f"p = {p:.3f}, significant" if p < 0.05 else f"p = {p:.2f}, not significant"


def ablation_rows(fam: pd.DataFrame, base: pd.DataFrame, base_ns: pd.DataFrame) -> list[dict[str, Any]]:
    """Ablation table with one template-generated takeaway per group."""
    rows: list[dict[str, Any]] = []
    for group, (regime, variants) in ABLATION_GROUPS.items():
        stats: dict[str, dict[str, dict[str, float]]] = {}
        values: dict[str, dict[str, np.ndarray]] = {}
        ref_label = next(label for _, label, is_ref in variants if is_ref)
        for family, label, _ in variants:
            values[label] = {m: series(fam, "family", family, regime, m) for m in ABLATION_METRICS}
            stats[label] = {m: s for m, v in values[label].items() if (s := stat_row(v))}
        present = [label for _, label, _ in variants if stats[label]]
        if ref_label not in present or len(present) < 2:
            continue

        def mean(label: str, metric: str, stats: dict = stats) -> float:
            return stats[label][metric]["mean"]

        def p(label: str, metric: str, values: dict = values, ref_label: str = ref_label) -> float | None:
            return clean_p(welch_p(values[label][metric], values[ref_label][metric]))

        others = [v for v in present if v != ref_label]
        if group == "fairness":
            o = others[0]
            takeaway = (
                f"Without the penalty the maximum wait goes from {mean(ref_label, 'max_wait'):.0f} s to "
                f"{mean(o, 'max_wait'):.0f} s ({pct(mean(o, 'max_wait'), mean(ref_label, 'max_wait')):+.0f}%, "
                f"{sig(p(o, 'max_wait'))}) and wait per person from {mean(ref_label, 'person_wait'):.1f} s to "
                f"{mean(o, 'person_wait'):.1f} s ({sig(p(o, 'person_wait'))})."
            )
        elif group == "weighting":
            o = others[0]
            takeaway = (
                f"Passenger weighting gives a bus delay of {mean(ref_label, 'delay_bus'):.1f} s against "
                f"{mean(o, 'delay_bus'):.1f} s with vehicle counting "
                f"({pct(mean(ref_label, 'delay_bus'), mean(o, 'delay_bus')):+.0f}%, {sig(p(o, 'delay_bus'))}); "
                f"car delay is {mean(ref_label, 'delay_car'):.1f} s against {mean(o, 'delay_car'):.1f} s "
                f"({sig(p(o, 'delay_car'))})."
            )
        elif group == "bus_weight":
            parts = ", ".join(f"{v}: {mean(v, 'delay_bus'):.1f} s" for v in present)
            spread = max(mean(v, "person_wait") for v in present) - min(mean(v, "person_wait") for v in present)
            takeaway = (f"Bus delay by assumed occupancy ({parts}). Wait per person varies by "
                        f"{spread:.1f} s across the three weights.")  # fmt: skip
        elif group == "sublane":
            o = others[0]
            takeaway = (
                f"With the sub-lane model off the agent's wait per person is {mean(o, 'person_wait'):.1f} s "
                f"against {mean(ref_label, 'person_wait'):.1f} s with it on. " + sublane_ranking(base, base_ns, fam)
            )
        else:
            best = min(present, key=lambda v: mean(v, "person_wait"))
            if best == ref_label:
                worst = max(others, key=lambda v: mean(v, "person_wait"))
                takeaway = (
                    f"The reference ({ref_label}) has the lowest wait per person, "
                    f"{mean(ref_label, 'person_wait'):.1f} s; the weakest variant ({worst}) reaches "
                    f"{mean(worst, 'person_wait'):.1f} s ({sig(p(worst, 'person_wait'))})."
                )
            else:
                takeaway = (
                    f"The lowest wait per person comes from '{best}' ({mean(best, 'person_wait'):.1f} s), "
                    f"not the reference ({ref_label}, {mean(ref_label, 'person_wait'):.1f} s; "
                    f"{sig(p(best, 'person_wait'))})."
                )
        for _, label, is_ref in variants:
            for metric, s in stats[label].items():
                rows.append({"group": group, "variant": label, "metric": metric, **s, "regime": regime,
                             "reference": is_ref, "takeaway": takeaway})  # fmt: skip
        if group == "sublane":
            for key in ("max_pressure", "fixed_matched", "actuated"):
                for tag, df in (("on", base), ("off", base_ns)):
                    name = f"{key}@nosublane" if tag == "off" else key
                    for metric in ABLATION_METRICS:
                        s = stat_row(series(df, "controller", name, regime, metric))
                        if s:
                            rows.append({"group": group, "variant": f"{CONTROLLER_LABELS[key]}, sub-lane {tag}",
                                         "metric": metric, **s, "regime": regime, "reference": False,
                                         "takeaway": takeaway})  # fmt: skip
    return rows


def sublane_ranking(base: pd.DataFrame, base_ns: pd.DataFrame, fam: pd.DataFrame) -> str:
    """Does the ranking of controllers by wait per person change without the sub-lane model?"""
    def rank(df: pd.DataFrame, suffix: str, agent_family: str) -> list[str]:
        scores = {}
        for key in ("fixed_matched", "actuated", "max_pressure"):
            v = series(df, "controller", key + suffix, "peak", "person_wait")
            if len(v):
                scores[CONTROLLER_LABELS[key]] = float(v.mean())
        v = series(fam, "family", agent_family, "peak", "person_wait")
        if len(v):
            scores["the agent"] = float(v.mean())
        return sorted(scores, key=scores.get)  # type: ignore[arg-type]

    on, off = rank(base, "", "abl_ref__peak"), rank(base_ns, "@nosublane", "abl_nosublane__peak")
    if len(on) < 3 or len(off) < 3:
        return "Baselines were not re-run without the sub-lane model."
    if on == off:
        return f"The ranking of controllers is unchanged ({' < '.join(on)})."
    return f"The ranking changes from {' < '.join(on)} to {' < '.join(off)}."


def pooled_waits(jobs_or_controller: list[str], regime: str) -> np.ndarray:
    parts = []
    for name in jobs_or_controller:
        path = WAITS / f"{name}__{regime}.npz"
        if path.exists():
            parts.append(np.load(path)["wait"])
    return np.concatenate(parts) if parts else np.array([])


def ecdf(waits: np.ndarray, points: int = 121) -> dict[str, Any]:
    q = np.linspace(0.0, 1.0, points)
    return {"ecdf_x": np.quantile(waits, q).round(2).tolist(), "ecdf_y": q.round(4).tolist(),
            "p50": float(np.median(waits)), "p95": float(np.quantile(waits, 0.95)),
            "max": float(waits.max())}  # fmt: skip


def better(a: float, b: float, metric: str) -> bool:
    return a < b if metric in LOWER_IS_BETTER else a > b


def write_json(name: str, obj: Any) -> Path:
    SUMMARY.mkdir(parents=True, exist_ok=True)
    path = SUMMARY / name
    path.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    return path
