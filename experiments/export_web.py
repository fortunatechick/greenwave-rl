"""Export everything the website shows into web/public/data/ (spec 11.1, 11.2).

    python experiments/export_web.py

Every file is validated against greenwave/web_schema.py before it is written, `mock` is
false, and every number comes from results/summary/. Sentences such as the KPI details
and the honest finding are filled from the numbers by fixed templates.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.aggregate import (  # noqa: E402
    ABLATION_GROUPS,
    CONTROLLER_LABELS,
    SUMMARY,
    ecdf,
    family_episodes,
    family_of,
    pooled_waits,
    read_episodes,
    series,
)  # fmt: skip
from greenwave.config import CLASSES, REGIMES, load_cfg  # noqa: E402
from greenwave.env.rewards import reward_params  # noqa: E402
from greenwave.jobs import family_jobs  # noqa: E402
from greenwave.metrics import welch_p  # noqa: E402
from greenwave.netjson import network_json  # noqa: E402
from greenwave.plan import sweep_choice  # noqa: E402
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

OUT = ROOT / "web" / "public" / "data"
MODELS = ROOT / "results" / "models"
WEB_METRICS = {"veh_wait", "person_wait", "avg_queue", "throughput", "max_wait", "wait_p95", "co2",
               "delay_bus", "forced_switches", "teleports"}  # fmt: skip
CURVE_FAMILIES = {"ddqn_fair": "ddqn_fair__peak", "dqn_sb3": "dqn_sb3__peak", "ppo": "ppo__peak"}
FAIRNESS = [
    ("skewed", "fair", "Passenger-weighted + fairness (ours)", "abl_ref__skewed"),
    ("skewed", "passenger_nofair", "No fairness penalty", "abl_nofair__skewed"),
    ("skewed", "max_pressure", "Max-pressure (reference)", None),
    ("peak", "fair", "Passenger-weighted + fairness (ours)", "abl_ref__peak"),
    ("peak", "vehicle_fair", "Vehicle-count + fairness", "abl_vehicle_fair__peak"),
    ("peak", "wait", "Waiting-time reward", "abl_reward_wait__peak"),
    ("peak", "queue", "Queue reward", "abl_reward_queue__peak"),
    ("peak", "pressure", "Pressure reward", "abl_reward_pressure__peak"),
]


def dump(name: str, obj: Any) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")


def archive_models() -> int:
    """Copy best checkpoints, configs, results and curves of every experiment job into
    results/models/ so that `make all` works from a fresh clone without retraining."""
    MODELS.mkdir(parents=True, exist_ok=True)
    (MODELS / "curves").mkdir(exist_ok=True)
    n = 0
    for flag in sorted((ROOT / "runs").glob("*/done.flag")):
        run = flag.parent
        if run.name.startswith(("smoke", "sweep", "toy")):
            continue
        for ext in ("pt", "zip"):
            if (run / f"best.{ext}").exists():
                shutil.copy2(run / f"best.{ext}", MODELS / f"best_{run.name}.{ext}")
        shutil.copy2(run / "config.json", MODELS / f"best_{run.name}.json")
        if (run / "result.json").exists():
            shutil.copy2(run / "result.json", MODELS / f"best_{run.name}.result.json")
        if (run / "curve.csv").exists():
            shutil.copy2(run / "curve.csv", MODELS / "curves" / f"{run.name}.csv")
        n += 1
    for name in ("plan.json", "status.json"):
        if (ROOT / "runs" / name).exists():
            shutil.copy2(ROOT / "runs" / name, SUMMARY / f"training_{name}")
    return n


def curves() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, family in CURVE_FAMILIES.items():
        frames = []
        for job in family_jobs(family):
            path = MODELS / "curves" / f"{job}.csv"
            if path.exists():
                frames.append(pd.read_csv(path).drop_duplicates("step", keep="last"))
        if not frames:
            continue
        last = min(int(f["step"].max()) for f in frames)
        first = max(int(f["step"].min()) for f in frames)
        grid = [s for s in range(10_000, last + 1, 10_000) if s >= first] or [last]
        runs = np.array([np.interp(grid, f["step"], f["val_score"]) for f in frames])
        out[key] = {"steps": grid, "mean": runs.mean(0).round(4).tolist(),
                    "std": (runs.std(0, ddof=1) if len(frames) > 1 else np.zeros(len(grid))).round(4).tolist(),
                    "n_seeds": len(frames)}  # fmt: skip
        Curve.model_validate(out[key])
    return out


def fairness() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for regime, design, label, family in FAIRNESS:
        names = family_jobs(family) if family else ["max_pressure"]
        waits = pooled_waits(names, regime)
        if len(waits) == 0:
            continue
        entry = {"label": label, "regime": regime, **ecdf(waits)}
        FairnessEntry.model_validate(entry)
        out[f"{design}@{regime}"] = entry
    return out


def deviations() -> list[str]:
    """Entries of DECISIONS.md marked [deviation], plus what the budget planner changed."""
    items: list[str] = []
    text = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
    for block in re.split(r"\n### ", text)[1:]:
        title = block.splitlines()[0]
        if "[deviation]" not in title:
            continue
        name = re.sub(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})? - ", "", title).replace("**[deviation]**", "").strip()
        done = re.search(r"\*\*Done instead:\*\*\s*(.+?)(?=\n- \*\*|\Z)", block, re.DOTALL)
        detail = " ".join(done.group(1).split()) if done else ""
        items.append(f"{name}. {detail}".strip())
    plan_path = SUMMARY / "training_plan.json"
    if plan_path.exists():
        items += json.loads(plan_path.read_text(encoding="utf-8")).get("deviations", [])
    status_path = SUMMARY / "training_status.json"
    if status_path.exists():
        jobs = json.loads(status_path.read_text(encoding="utf-8")).get("jobs", {})
        failed = [n for n, j in jobs.items() if j.get("state") != "done"]
        if failed:
            items.append(f"{len(failed)} training job(s) did not finish and are missing: {', '.join(failed)}.")
    return items


def lookup(table: pd.DataFrame, regime: str, controller: str, metric: str) -> dict[str, Any] | None:
    sel = table[(table.regime == regime) & (table.controller == controller) & (table.metric == metric)]
    return None if sel.empty else sel.iloc[0].to_dict()


def honest_finding(table: pd.DataFrame) -> str:
    def split(metric: str) -> tuple[list[str], list[str], list[str]]:
        wins, losses, ties = [], [], []
        for regime in REGIMES:
            rl = lookup(table, regime, "ddqn_fair", metric)
            mp = lookup(table, regime, "max_pressure", metric)
            if not rl or not mp:
                continue
            p = rl["p_vs_mp"]
            if p is None or not np.isfinite(p) or p >= 0.05:
                ties.append(regime)
            elif rl["mean"] < mp["mean"]:
                wins.append(regime)
            else:
                losses.append(regime)
        return wins, losses, ties

    def phrase(items: list[str], empty: str = "no regime") -> str:
        return ", ".join(items) if items else empty

    if lookup(table, "peak", "ddqn_fair", "person_wait") is None:
        return ""
    w, lo, t = split("person_wait")
    mw, ml, mt = split("max_wait")
    beats_fixed = [r for r in REGIMES if (a := lookup(table, r, "ddqn_fair", "person_wait"))
                   and (b := lookup(table, r, "fixed_matched", "person_wait")) and a["mean"] < b["mean"]
                   and a["p_vs_fixed"] is not None and a["p_vs_fixed"] < 0.05]  # fmt: skip
    return (
        f"Against a fixed-time plan tuned for each demand pattern, the regime-matched Double DQN cuts wait per "
        f"person significantly in {len(beats_fixed)} of {len(REGIMES)} regimes ({phrase(beats_fixed)}). Against "
        f"max-pressure, a rule that needs no training, it is significantly better on wait per person in "
        f"{phrase(w)}, significantly worse in {phrase(lo)}, and statistically tied in {phrase(t)}. On the maximum "
        f"wait it is better in {phrase(mw)}, worse in {phrase(ml)} and tied in {phrase(mt)}. Significance is a "
        f"Welch t-test over 10 held-out seeds at p < 0.05."
    )


def kpis(table: pd.DataFrame, ablations: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    def abl(group: str, variant: str, metric: str) -> float | None:
        for r in ablations:
            if r["group"] == group and r["variant"] == variant and r["metric"] == metric:
                return float(r["mean"])
        return None

    def change(new: float | None, old: float | None) -> float | None:
        return None if new is None or old is None or old == 0 else 100.0 * (new - old) / old

    rl = lookup(table, "surge", "ddqn_fair", "person_wait")
    fixed = lookup(table, "surge", "fixed_matched", "person_wait")
    mp = lookup(table, "surge", "max_pressure", "person_wait")
    headline = {"regime": "surge", "metric": "person_wait",
                "rl": rl["mean"] if rl else None, "fixed": fixed["mean"] if fixed else None,
                "max_pressure": mp["mean"] if mp else None}  # fmt: skip

    fair_ref, fair_off = ABLATION_GROUPS["fairness"][1][0][1], ABLATION_GROUPS["fairness"][1][1][1]
    w_ref, w_off = ABLATION_GROUPS["weighting"][1][0][1], ABLATION_GROUPS["weighting"][1][1][1]
    fam = family_episodes(read_episodes("agents"))

    def tested(fam_a: str, fam_b: str, regime: str, metric: str) -> str:
        p = welch_p(series(fam, "family", fam_a, regime, metric), series(fam, "family", fam_b, regime, metric))
        if not np.isfinite(p):
            return ""
        return f"; p = {p:.3f}, significant" if p < 0.05 else f"; p = {p:.2f}, not statistically significant"

    a, b = abl("fairness", fair_ref, "max_wait"), abl("fairness", fair_off, "max_wait")
    c, d = abl("weighting", w_ref, "delay_bus"), abl("weighting", w_off, "delay_bus")
    tiles = [
        {"key": "surge", "label": "Wait per person vs fixed-time, surge regime",
         "value": change(headline["rl"], headline["fixed"]),
         "detail": (f"{headline['rl']:.1f} s against {headline['fixed']:.1f} s with a Webster plan tuned for the surge"
                    if rl and fixed else "evaluation pending")},
        {"key": "fair", "label": "Longest wait vs an agent without the fairness penalty",
         "value": change(a, b),
         "detail": (f"{a:.0f} s against {b:.0f} s, skewed regime, budget-matched runs"
                    + tested("abl_ref__skewed", "abl_nofair__skewed", "skewed", "max_wait")
                    if a is not None and b is not None else "ablation pending")},
        {"key": "bus", "label": "Bus delay vs a vehicle-count reward",
         "value": change(c, d),
         "detail": (f"{c:.1f} s against {d:.1f} s, peak regime, budget-matched runs"
                    + tested("abl_ref__peak", "abl_vehicle_fair__peak", "peak", "delay_bus")
                    if c is not None and d is not None else "ablation pending")},
    ]  # fmt: skip
    return headline, tiles


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> None:
    cfg = load_cfg()
    n_models = archive_models()

    table_path = SUMMARY / "main_table.csv"
    if not table_path.exists():
        sys.exit("results/summary/main_table.csv missing: run experiments/generalisation.py first")
    table = pd.read_csv(table_path)
    table = table.astype(object).where(table.notna(), None)

    main_rows = [r for r in table.to_dict(orient="records") if r["metric"] in WEB_METRICS]
    for r in main_rows:
        r["n"] = int(r["n"])
        MainRow.model_validate(r)
    dump("results/main.json", main_rows)

    per_class = []
    for r in table.to_dict(orient="records"):
        if str(r["metric"]).startswith("delay_") and r["metric"].removeprefix("delay_") in CLASSES:
            row = {"regime": r["regime"], "controller": r["controller"], "class": r["metric"].removeprefix("delay_"),
                   "delay_mean": r["mean"], "delay_std": r["std"]}  # fmt: skip
            PerClassRow.model_validate(row)
            per_class.append(row)
    dump("results/per_class.json", per_class)

    dump("results/curves.json", curves())

    gens = []
    gen_path = SUMMARY / "generalisation.json"
    for g in json.loads(gen_path.read_text(encoding="utf-8")) if gen_path.exists() else []:
        g = {k: v for k, v in g.items() if k in Generalisation.model_fields}
        Generalisation.model_validate(g)
        gens.append(g)
    dump("results/generalisation.json", gens)

    dump("results/fairness.json", fairness())

    abl_path = SUMMARY / "ablations.json"
    ablations = json.loads(abl_path.read_text(encoding="utf-8")) if abl_path.exists() else []
    for r in ablations:
        AblationRow.model_validate(r)
    dump("results/ablations.json", ablations)

    net = network_json()
    Network.model_validate(net)
    dump("network.json", net)

    demand_meta = json.loads((ROOT / "demand" / "demand_meta.json").read_text(encoding="utf-8"))
    dump("demand.json", {"regimes": demand_meta["regimes"], "pcu": cfg["demand"]["pcu"],
                         "passenger_weights": cfg["demand"]["passenger_weights"],
                         "class_mix": cfg["demand"]["class_mix"], "classes": list(CLASSES)})  # fmt: skip

    choice = sweep_choice() or {}
    params = reward_params(**choice)
    plan_path = SUMMARY / "training_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    agents = read_episodes("agents")
    train_seeds = 0
    if not agents.empty:
        fams = agents["controller"].map(family_of)
        train_seeds = int(agents[fams == "ddqn_fair__peak"]["controller"].nunique())
    headline, tiles = kpis(pd.read_csv(table_path), ablations)
    meta = {
        "mock": False,
        "profile": plan.get("profile", "unknown"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_sha": git_sha(),
        "synthetic_demand": bool(demand_meta["synthetic_demand"]),
        "junction_name": cfg["junction"]["name"],
        "network_source": "osm" if cfg["junction"].get("bbox") else "plain",
        "sumo_version": version("eclipse-sumo"),
        "seeds": {"train": train_seeds, "eval": int(read_episodes("baselines")["seed"].nunique())},
        "deviations": deviations(),
        "headline": headline,
        "kpis": tiles,
        "honest_finding": honest_finding(pd.read_csv(table_path)),
        "reward": {"lambda": params["lam"], "T": params["T"], "kappa": params["kappa"],
                   "mean_occupancy": params["mean_occupancy"]},
        "controllers": CONTROLLER_LABELS,
    }  # fmt: skip
    Meta.model_validate(meta)
    dump("meta.json", meta)

    replays = sorted((OUT / "replays").glob("*.json"))
    mock = [p.name for p in replays if json.loads(p.read_text(encoding="utf-8")).get("mock")]
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"exported to {OUT.relative_to(ROOT)}: {len(main_rows)} main rows, {len(ablations)} ablation rows, "
          f"{n_models} checkpoints archived, {len(replays)} replays, {size:.1f} MB total")  # fmt: skip
    if mock:
        print(f"WARNING: mock replays still present: {mock}. Run experiments/record_replay.py")
    print("honest finding:", meta["honest_finding"])
    for t in tiles:
        print(f"  KPI {t['key']}: {t['value']}  ({t['detail']})")


if __name__ == "__main__":
    main()
