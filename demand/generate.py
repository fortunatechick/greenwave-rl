"""Generate demand: counts.csv, route files for the four regimes, the domain-randomisation
pool, the toy routes, and the Webster fixed-time programs that depend on the flows.

    python demand/generate.py            # everything
    python demand/generate.py --toy      # toy routes only
    python demand/generate.py --keep-counts   # use an existing (field) demand/counts.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.config import CLASS_CODES, CLASSES, REGIMES, load_cfg  # noqa: E402
from greenwave.controllers.fixed_time import (  # noqa: E402
    WebsterPlan,
    fixed_program_file,
    webster_plan,
)
from greenwave.tls import dest_of, program_xml, read_layout, write_program_file  # noqa: E402

TURNS = ("left", "through", "right")
Segment = dict[str, Any]  # approach, turn, cls, begin, end, vph


def sat_flows(cfg: dict) -> dict[str, float]:
    j, d = cfg["junction"], cfg["demand"]
    return {
        a: d["saturation_flow_per_m"] * j["lanes_in"][a] * j["lane_width_m"] for a in j["approaches"]
    }


def mean_pcu(d: dict) -> float:
    return sum(d["class_mix"][c] * d["pcu"][c] for c in CLASSES)


def plan_for(cfg: dict, flows_pcu: dict[str, float]) -> WebsterPlan:
    s = cfg["sim"]
    return webster_plan(
        flows_pcu,
        sat_flows(cfg),
        yellow=s["yellow"],
        all_red=s["all_red"],
        startup_loss=s["startup_loss"],
        min_green=s["min_green"],
        max_green=s["max_green"],
    )


def calibrate_peak(cfg: dict) -> dict[str, float]:
    """PCU/h per approach such that the Webster plan sits at the target degree of saturation."""
    j, d = cfg["junction"], cfg["demand"]
    unit = {a: (d["major_ratio"] if a in d["major_approaches"] else 1.0) for a in j["approaches"]}
    lo, hi = 1.0, 5000.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        x = plan_for(cfg, {a: mid * u for a, u in unit.items()}).saturation_design
        if x < d["target_saturation"]:
            lo = mid
        else:
            hi = mid
    return {a: lo * u * d["peak_scale"] for a, u in unit.items()}


def synthetic_counts(cfg: dict) -> pd.DataFrame:
    d = cfg["demand"]
    peak_pcu = calibrate_peak(cfg)
    rows = []
    for period, scale in (("peak", 1.0), ("offpeak", d["regimes"]["low"]["scale"])):
        for a, q in peak_pcu.items():
            veh = q / mean_pcu(d) * scale
            for turn in TURNS:
                for c in CLASSES:
                    rows.append(
                        {
                            "approach": a,
                            "turn": turn,
                            "class": c,
                            "veh_per_hour": round(veh * d["turn_split"][turn] * d["class_mix"][c], 2),
                            "period": period,
                        }
                    )
    return pd.DataFrame(rows)


def peak_table(counts: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    peak = counts[counts["period"] == "peak"]
    return {(r.approach, r.turn, r["class"]): float(r.veh_per_hour) for _, r in peak.iterrows()}


def regime_segments(
    peak: dict[tuple[str, str, str], float], regime_cfg: dict, horizon: int
) -> list[Segment]:
    segs: list[Segment] = []
    boosted = regime_cfg.get("boosted", {})
    burst = regime_cfg.get("burst")
    for (a, turn, c), vph in peak.items():
        scale = boosted.get(a, regime_cfg["scale"])
        segs.append({"approach": a, "turn": turn, "cls": c, "begin": 0, "end": horizon, "vph": vph * scale})
        if burst and burst["approach"] == a:
            segs.append(
                {
                    "approach": a,
                    "turn": turn,
                    "cls": c,
                    "begin": burst["begin"],
                    "end": burst["end"],
                    "vph": vph * (burst["scale"] - scale),
                }
            )
    return segs


def scaled_segments(
    peak: dict[tuple[str, str, str], float], factors: dict[str, float], horizon: int
) -> list[Segment]:
    return [
        {"approach": a, "turn": t, "cls": c, "begin": 0, "end": horizon, "vph": v * factors[a]}
        for (a, t, c), v in peak.items()
    ]


def approach_pcu(segs: list[Segment], pcu: dict[str, float], horizon: int) -> dict[str, float]:
    """Time-averaged PCU/h per approach."""
    out: dict[str, float] = {}
    for s in segs:
        share = (s["end"] - s["begin"]) / horizon
        out[s["approach"]] = out.get(s["approach"], 0.0) + s["vph"] * pcu[s["cls"]] * share
    return out


def write_routes(path: Path, segs: list[Segment]) -> int:
    """Poisson arrivals: one <flow period="exp(rate)"> per (origin, destination, class, window).
    Vehicle ids read `<origin>-<dest>-<class code>-<window>.<n>` so class and approach can be
    recovered from the id alone."""
    lines = ["<routes>"]
    counter: dict[tuple[str, str, str], int] = {}
    n = 0
    for s in sorted(segs, key=lambda s: (s["begin"], s["approach"], s["turn"], s["cls"])):
        if s["vph"] < 0.5:
            continue
        dest = dest_of(s["approach"], s["turn"])
        key = (s["approach"], dest, s["cls"])
        k = counter.get(key, 0)
        counter[key] = k + 1
        lines.append(
            f'    <flow id="{s["approach"]}-{dest}-{CLASS_CODES[s["cls"]]}-{k}" type="{s["cls"]}" '
            f'from="{s["approach"]}_in" to="{dest}_out" begin="{s["begin"]}" end="{s["end"]}" '
            f'period="exp({s["vph"] / 3600.0:.6f})" departLane="best" departSpeed="max"/>'
        )
        n += 1
    lines.append("</routes>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n


def write_toy(cfg: dict) -> None:
    """Strongly unbalanced demand on the single-lane toy junction."""
    d = cfg["demand"]
    volume = {"N": 600.0, "S": 500.0, "E": 80.0, "W": 80.0}
    segs = [
        {
            "approach": a, "turn": t, "cls": c, "begin": 0, "end": cfg["sim"]["episode_seconds"],
            "vph": v * d["turn_split"][t] * d["class_mix"][c],
        }
        for a, v in volume.items() for t in TURNS for c in CLASSES
    ]  # fmt: skip
    n = write_routes(ROOT / "network" / "toy" / "toy.rou.xml", segs)
    print(f"toy routes: {n} flows, {sum(volume.values()):.0f} veh/h")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toy", action="store_true")
    parser.add_argument("--keep-counts", action="store_true")
    args = parser.parse_args()
    cfg = load_cfg()
    d, sim, j = cfg["demand"], cfg["sim"], cfg["junction"]
    horizon = sim["episode_seconds"]

    write_toy(cfg)
    if args.toy:
        return

    counts_path = ROOT / "demand" / "counts.csv"
    synthetic = not (args.keep_counts and counts_path.exists())
    if synthetic:
        synthetic_counts(cfg).to_csv(counts_path, index=False)
    counts = pd.read_csv(counts_path)
    peak = peak_table(counts)

    layout = read_layout(ROOT / "network" / "junction.net.xml", j["approaches"], j["free_left"])
    meta: dict[str, Any] = {
        "synthetic_demand": synthetic,
        "mean_pcu_per_vehicle": mean_pcu(d),
        "saturation_flows_pcu_h": sat_flows(cfg),
        "regimes": {},
    }
    for regime in REGIMES:
        segs = regime_segments(peak, d["regimes"][regime], horizon)
        n = write_routes(ROOT / "demand" / "routes" / f"{regime}.rou.xml", segs)
        flows = approach_pcu(segs, d["pcu"], horizon)
        plan = plan_for(cfg, flows)
        greens = [plan.greens[a] for a in j["approaches"]]
        write_program_file(
            fixed_program_file(regime),
            program_xml(layout, greens, sim["yellow"], sim["all_red"], program_id=f"fixed_{regime}"),
        )
        veh_by_class = {c: 0.0 for c in CLASSES}
        veh_by_approach = {a: 0.0 for a in j["approaches"]}
        for s in segs:
            share = (s["end"] - s["begin"]) / horizon
            veh_by_class[s["cls"]] += s["vph"] * share
            veh_by_approach[s["approach"]] += s["vph"] * share
        meta["regimes"][regime] = {
            "pcu_per_hour": {a: round(v, 1) for a, v in flows.items()},
            "veh_per_hour_by_approach": {a: round(v, 1) for a, v in veh_by_approach.items()},
            "veh_per_hour_by_class": {c: round(v, 1) for c, v in veh_by_class.items()},
            "webster": {
                "cycle": plan.cycle,
                "greens": plan.greens,
                "Y": round(plan.Y, 4),
                "saturation": {a: round(x, 3) for a, x in plan.saturation.items()},
            },
        }
        print(
            f"{regime:7s} {n:3d} flows  {sum(veh_by_class.values()):6.0f} veh/h  "
            f"Webster C={plan.cycle:.0f}s greens={greens} "
            f"x={max(plan.saturation.values()):.2f}"
        )

    rng = np.random.default_rng(d["dr_pool"]["seed"])
    pool = ROOT / "demand" / "dr_pool"
    pool.mkdir(parents=True, exist_ok=True)
    for old in pool.glob("dr_*.rou.xml"):
        old.unlink()
    for i in range(d["dr_pool"]["size"]):
        factors = {
            a: float(rng.uniform(d["dr_pool"]["low"], d["dr_pool"]["high"])) for a in j["approaches"]
        }
        write_routes(pool / f"dr_{i:03d}.rou.xml", scaled_segments(peak, factors, horizon))
    print(f"domain-randomisation pool: {d['dr_pool']['size']} files")

    (ROOT / "demand" / "demand_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
