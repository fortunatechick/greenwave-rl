"""Generate web/fixtures/: preview data for building the site before training finishes.

Everything here is flagged "mock": true. Baseline rows are real; every RL number is a
random perturbation of max-pressure and means nothing. The production build refuses to
ship these files (web/scripts/check-data.mjs).

    python experiments/make_fixtures.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.record_replay import SCENES, record_scene  # noqa: E402
from greenwave.config import CLASSES, REGIMES, load_cfg  # noqa: E402
from greenwave.netjson import network_json  # noqa: E402
from greenwave.web_schema import (  # noqa: E402
    AblationRow,
    Curve,
    FairnessEntry,
    Generalisation,
    MainRow,
    Meta,
    Network,
    PerClassRow,
)  # fmt: skip

OUT = ROOT / "web" / "fixtures"
RL = {"ddqn_fair": 0.95, "ddqn_fair_dr": 1.02, "dqn_sb3": 1.08, "ppo": 1.12}
LABELS = {
    "fixed_matched": "Fixed-time (matched)", "fixed_peak": "Fixed-time (peak plan)",
    "actuated": "Actuated", "max_pressure": "Max-pressure", "random": "Random",
    "ddqn_fair": "Double DQN, fair (ours)", "ddqn_fair_dr": "Double DQN, fair + DR (ours)",
    "dqn_sb3": "DQN (SB3)", "ppo": "PPO (SB3)",
}  # fmt: skip


def dump(name: str, obj: object) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    rng = np.random.default_rng(0)
    cfg = load_cfg()
    base = pd.read_csv(ROOT / "results" / "summary" / "baselines.csv")
    rows = []
    for r in base.itertuples():
        rows.append({"regime": r.regime, "controller": r.controller, "metric": r.metric,
                     "mean": float(r.mean), "std": float(r.std), "n": int(r.n),
                     "p_vs_fixed": None, "p_vs_mp": None})  # fmt: skip
    mp = base[base.controller == "max_pressure"]
    for key, factor in RL.items():
        for r in mp.itertuples():
            f = 1.0 if r.metric == "throughput" else factor * rng.uniform(0.9, 1.1)
            rows.append({"regime": r.regime, "controller": key, "metric": r.metric,
                         "mean": float(r.mean * f), "std": float(r.std), "n": 10,
                         "p_vs_fixed": 0.001, "p_vs_mp": float(rng.uniform(0, 0.4))})  # fmt: skip
    rows = [r for r in rows if np.isfinite(r["mean"]) and np.isfinite(r["std"])]
    for r in rows:
        MainRow.model_validate(r)
    dump("results/main.json", rows)

    steps = list(range(10_000, 100_001, 10_000))
    curves = {}
    for i, agent in enumerate(("ddqn_fair", "dqn_sb3", "ppo")):
        mean = [-1.5 * np.exp(-s / 30_000) - 0.2 - 0.05 * i for s in steps]
        curves[agent] = {"steps": steps, "mean": mean, "std": [0.1 + 0.02 * i] * len(steps), "n_seeds": 3}
        Curve.model_validate(curves[agent])
    dump("results/curves.json", curves)

    gens = []
    for metric, lo in (("person_wait", 12.0), ("max_wait", 90.0)):
        m = [[lo * (1.0 if a == b else rng.uniform(1.2, 2.2)) for b in range(4)] for a in range(4)]
        g = {"metric": metric, "regimes": list(REGIMES), "matrix": m,
             "std": [[lo * 0.08] * 4 for _ in range(4)], "dr_row": [lo * 1.1] * 4,
             "dr_std": [lo * 0.08] * 4, "gap_recovered_pct": 71.0}  # fmt: skip
        Generalisation.model_validate(g)
        gens.append(g)
    dump("results/generalisation.json", gens)

    fairness = {}
    for key, label, scale in (("fair", "Passenger-weighted + fairness (ours)", 14.0),
                              ("passenger_nofair", "No fairness penalty", 18.0),
                              ("vehicle_fair", "Vehicle-count + fairness", 15.0),
                              ("wait", "Waiting-time baseline", 16.0)):  # fmt: skip
        x = np.sort(rng.gamma(1.2, scale, 4000))
        q = np.linspace(0, 1, 101)
        e = {"label": label, "regime": "skewed", "ecdf_x": np.quantile(x, q).round(1).tolist(),
             "ecdf_y": q.round(3).tolist(), "p50": float(np.median(x)),
             "p95": float(np.quantile(x, 0.95)), "max": float(x.max())}  # fmt: skip
        FairnessEntry.model_validate(e)
        fairness[f"{key}@skewed"] = e
    dump("results/fairness.json", fairness)

    per_class = []
    for r in rows:
        if r["metric"].startswith("delay_"):
            row = {"regime": r["regime"], "controller": r["controller"],
                   "class": r["metric"].removeprefix("delay_"), "delay_mean": r["mean"],
                   "delay_std": r["std"]}  # fmt: skip
            PerClassRow.model_validate(row)
            per_class.append(row)
    dump("results/per_class.json", per_class)

    ablations = []
    groups = {"reward": ["ours", "wait", "queue", "pressure"], "fairness": ["ours", "no penalty"],
              "weighting": ["passenger", "vehicle"], "bus_weight": ["20", "40", "60"],
              "state": ["full", "no timer", "no max-wait"], "interval": ["5 s", "10 s", "15 s"],
              "sublane": ["on", "off"]}  # fmt: skip
    for group, variants in groups.items():
        for i, v in enumerate(variants):
            for metric, lo in (("person_wait", 16.0), ("max_wait", 100.0), ("delay_bus", 30.0)):
                row = {"group": group, "variant": v, "metric": metric,
                       "mean": float(lo * rng.uniform(0.9, 1.4)), "std": float(lo * 0.1), "n": 20,
                       "regime": "skewed" if group == "fairness" else "peak", "reference": i == 0,
                       "takeaway": "Preview takeaway, generated from mock numbers."}  # fmt: skip
                AblationRow.model_validate(row)
                ablations.append(row)
    dump("results/ablations.json", ablations)

    net = network_json()
    Network.model_validate(net)
    dump("network.json", net)

    demand_meta = json.loads((ROOT / "demand" / "demand_meta.json").read_text(encoding="utf-8"))
    dump("demand.json", {"regimes": demand_meta["regimes"], "pcu": cfg["demand"]["pcu"],
                         "passenger_weights": cfg["demand"]["passenger_weights"],
                         "class_mix": cfg["demand"]["class_mix"], "classes": list(CLASSES)})  # fmt: skip

    road = {"left_delay_s": 30.0, "right_delay_s": 20.0, "left_trip_s": 3900.0, "right_trip_s": 3800.0,
            "saved_s": 100.0, "saved_std_s": 20.0, "n_seeds": 10}  # fmt: skip
    dump("corridor.json", {
        "length_km": 100.0, "signals": 10, "speed_kmh": 100.0, "free_flow_s": 3600.0, "mock": True,
        "vehicle": "car, straight through",
        "scenes": {name: {"regime": "peak", "left": "fixed_peak", "right": "max_pressure",
                           "roads": {"major": road, "minor": road}} for name in SCENES},
    })  # fmt: skip

    meta = {
        "mock": True, "profile": "fixture", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_sha": "fixture", "synthetic_demand": True, "junction_name": cfg["junction"]["name"],
        "network_source": "plain", "sumo_version": "1.28.0", "seeds": {"train": 3, "eval": 10},
        "deviations": ["Preview fixture: RL numbers are placeholders."],
        "headline": {"regime": "surge", "metric": "person_wait", "rl": 16.0, "fixed": 36.4,
                     "max_pressure": 17.6},
        "kpis": [
            {"key": "surge", "label": "Person wait vs fixed-time, surge", "value": -56.0, "detail": "mock"},
            {"key": "fair", "label": "Max wait vs no-fairness agent", "value": -38.0, "detail": "mock"},
            {"key": "bus", "label": "Bus delay vs vehicle-count reward", "value": None, "detail": "mock"},
        ],
        "honest_finding": "Preview text: where RL beats and loses to max-pressure is filled from data.",
        "reward": {"lambda": 1.0, "T": 90.0, "kappa": 100.0},
        "controllers": LABELS,
    }  # fmt: skip
    Meta.model_validate(meta)
    dump("meta.json", meta)

    # One real recording with baselines standing in for the agents, reused for every scene.
    stand_in = {"regime": "peak", "left": "fixed_peak", "right": "max_pressure", "t0": 600, "t1": 840}
    for name, scene in SCENES.items():
        mock_scene = {**scene, **stand_in, "events": []}
        if name == "surge":
            mock_scene["events"] = [{"t": 700, "label": "Mock event marker"}]
        record_scene(name, mock_scene, 1000, OUT / "replays", mock=True,
                     labels={"max_pressure": "Max-pressure (stand-in for the agent)"})  # fmt: skip
    print(f"fixtures written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
