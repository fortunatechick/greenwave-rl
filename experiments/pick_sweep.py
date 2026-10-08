"""Pick lambda and T from the sweep (spec 4.3): lowest person delay on the skewed regime
subject to max wait <= 1.2 T. Uses the selection seeds, which are neither training nor
evaluation seeds. Writes results/summary/sweep_choice.json and logs to DECISIONS.md.

    python experiments/pick_sweep.py --workers 7
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.config import load_cfg  # noqa: E402
from greenwave.jobs import JobSpec  # noqa: E402
from greenwave.plan import SWEEP_CHOICE  # noqa: E402
from greenwave.runner import make_controller, run_episode  # noqa: E402


def _episode(task: tuple[str, int]) -> dict[str, Any]:
    job, seed = task
    import torch

    torch.set_num_threads(1)
    spec = JobSpec.load(ROOT / "runs" / job / "config.json")
    out = run_episode(make_controller(job, spec.regime), spec.regime, seed)
    m = out["metrics"]
    return {"job": job, "lam": spec.lam, "T": spec.T, "seed": seed,
            "person_wait": m["person_wait"], "max_wait": m["max_wait"], "veh_wait": m["veh_wait"]}  # fmt: skip


def pick(table: pd.DataFrame) -> tuple[dict[str, Any], str]:
    table = table.copy()
    table["feasible"] = table["max_wait"] <= 1.2 * table["T"]
    feasible = table[table["feasible"]]
    if len(feasible):
        row = feasible.sort_values("person_wait").iloc[0]
        rule = "lowest person delay among settings with max wait <= 1.2 T"
    else:
        table["violation"] = table["max_wait"] / (1.2 * table["T"])
        row = table.sort_values(["violation", "person_wait"]).iloc[0]
        rule = "no setting met max wait <= 1.2 T; chose the smallest relative violation"
    return {"lam": float(row["lam"]), "T": float(row["T"]),
            "person_wait": float(row["person_wait"]), "max_wait": float(row["max_wait"])}, rule  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=7)
    args = parser.parse_args()
    jobs = sorted(p.parent.name for p in (ROOT / "runs").glob("sweep_*/done.flag"))
    if not jobs:
        sys.exit("no finished sweep jobs")
    lo, hi = load_cfg()["sim"]["seeds"]["selection"]
    tasks = [(j, s) for j in jobs for s in range(lo, hi + 1)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(_episode, tasks))
    episodes = pd.DataFrame(rows)
    table = episodes.groupby(["job", "lam", "T"], as_index=False)[
        ["person_wait", "max_wait", "veh_wait"]
    ].mean()
    chosen, rule = pick(table)
    table["feasible"] = table["max_wait"] <= 1.2 * table["T"]
    SWEEP_CHOICE.parent.mkdir(parents=True, exist_ok=True)
    SWEEP_CHOICE.write_text(
        json.dumps({"chosen": chosen, "rule": rule, "seeds": [lo, hi],
                    "table": table.round(3).to_dict(orient="records")}, indent=2),
        encoding="utf-8",
    )  # fmt: skip
    print(table.round(1).to_string(index=False))
    print(f"chosen lambda={chosen['lam']:g}, T={chosen['T']:g}  ({rule})")

    with open(ROOT / "DECISIONS.md", "a", encoding="utf-8") as fh:
        fh.write(
            f"\n### {time.strftime('%Y-%m-%d %H:%M')} - lambda / T sweep\n"
            f"- **What:** 9 short Double DQN runs on the skewed regime, lambda in {{0.25, 1, 4}} x "
            f"T in {{60, 90, 120}}, scored on selection seeds {lo}-{hi}.\n"
            f"- **Chosen:** lambda = {chosen['lam']:g}, T = {chosen['T']:g} s "
            f"(person wait {chosen['person_wait']:.1f} s, max wait {chosen['max_wait']:.0f} s).\n"
            f"- **Rule applied:** {rule}.\n"
            f"- **Effect:** every main and ablation run uses these values.\n"
        )


if __name__ == "__main__":
    main()
