"""Evaluation metrics from SUMO tripinfo output (spec Section 8.2)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from greenwave.config import CLASSES, CODE_INDEX, class_vector, load_cfg

# Metrics where a lower value is better (used for bolding and arrows downstream).
LOWER_IS_BETTER = {
    "veh_wait", "person_wait", "avg_queue", "max_wait", "wait_p95", "co2",
    "delay_two_wheeler", "delay_auto_rickshaw", "delay_car", "delay_bus",
    "forced_switches", "teleports", "depart_delay",
}  # fmt: skip
MAIN_METRICS = ("veh_wait", "person_wait", "avg_queue", "throughput", "max_wait", "wait_p95", "co2")


def parse_tripinfo(path: str | Path) -> pd.DataFrame:
    """One row per vehicle that entered the network (unfinished ones have arrival < 0)."""
    rows: list[tuple[Any, ...]] = []
    for _, el in ET.iterparse(str(path), events=("end",)):
        if el.tag != "tripinfo":
            continue
        vid = el.get("id", "")
        parts = vid.split("-")
        emissions = el.find("emissions")
        rows.append(
            (
                vid,
                parts[0],
                parts[1],
                CODE_INDEX[parts[2]],
                float(el.get("depart", "0")),
                float(el.get("arrival", "-1")),
                float(el.get("waitingTime", "0")),
                float(el.get("timeLoss", "0")),
                float(el.get("departDelay", "0")),
                float(emissions.get("CO2_abs", "0")) if emissions is not None else np.nan,
            )
        )
        el.clear()
    return pd.DataFrame(
        rows,
        columns=["id", "approach", "dest", "cls", "depart", "arrival", "wait", "time_loss",
                 "depart_delay", "co2_mg"],
    )  # fmt: skip


def episode_metrics(
    trips: pd.DataFrame,
    env_stats: Mapping[str, float],
    weights: np.ndarray | None = None,
    approaches: tuple[str, ...] = ("N", "E", "S", "W"),
) -> dict[str, float]:
    if weights is None:
        weights = np.asarray(class_vector(load_cfg()["demand"]["passenger_weights"]))
    seconds = float(env_stats.get("seconds", 3600.0))
    out: dict[str, float] = {}
    if trips.empty:
        return {"veh_wait": np.nan, "person_wait": np.nan}
    w = weights[trips["cls"].to_numpy()]
    wait = trips["wait"].to_numpy()
    out["veh_wait"] = float(wait.mean())
    out["person_wait"] = float((w * wait).sum() / w.sum())
    out["avg_queue"] = float(env_stats.get("avg_queue", np.nan))
    out["throughput"] = float((trips["arrival"] >= 0).sum() * 3600.0 / seconds)
    per_approach = trips.groupby("approach")["wait"].max()
    for a in approaches:
        out[f"max_wait_{a}"] = float(per_approach.get(a, 0.0))
    out["max_wait"] = float(per_approach.max())
    out["wait_p95"] = float(np.percentile(wait, 95))
    for i, c in enumerate(CLASSES):
        sel = trips["cls"] == i
        out[f"delay_{c}"] = float(trips.loc[sel, "time_loss"].mean()) if sel.any() else np.nan
        out[f"wait_{c}"] = float(trips.loc[sel, "wait"].mean()) if sel.any() else np.nan
    out["co2"] = float(trips["co2_mg"].mean() / 1000.0)
    out["depart_delay"] = float(trips["depart_delay"].mean())
    out["n_vehicles"] = float(len(trips))
    out["forced_switches"] = float(env_stats.get("forced_switches", 0.0))
    out["switches"] = float(env_stats.get("switches", 0.0))
    out["teleports"] = float(env_stats.get("teleports", 0.0))
    out["teleport_pct"] = 100.0 * out["teleports"] / max(len(trips), 1)
    out["collisions"] = float(env_stats.get("collisions", 0.0))
    out["pending"] = float(env_stats.get("pending", 0.0))
    out["episode_reward"] = float(env_stats.get("episode_reward", np.nan))
    return out


def summarise(episodes: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Long table: one row per (group, metric) with mean, std and n over seeds."""
    id_cols = set(by) | {"seed"}
    metric_cols = [c for c in episodes.columns if c not in id_cols and episodes[c].dtype != object]
    long = episodes.melt(id_vars=by, value_vars=metric_cols, var_name="metric")
    grouped = long.groupby([*by, "metric"])["value"]
    out = grouped.agg(mean="mean", std=lambda s: s.std(ddof=1) if len(s) > 1 else 0.0, n="count")
    return out.reset_index()


def welch_p(a: np.ndarray, b: np.ndarray) -> float:
    """Two-sided Welch t-test p-value; NaN when either sample is degenerate."""
    from scipy import stats

    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(a) < 2 or len(b) < 2 or (a.std() == 0 and b.std() == 0):
        return float("nan")
    return float(stats.ttest_ind(a, b, equal_var=False).pvalue)
