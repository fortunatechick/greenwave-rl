"""Evaluate controllers: every (controller, regime, eval seed) episode in parallel.

    python experiments/evaluate.py --baselines             # the five baselines, 4 regimes
    python experiments/evaluate.py --agents                # every finished training job
    python experiments/evaluate.py --controllers max_pressure --regimes peak --seeds 2

Outputs (results/summary/):
    episodes_<tag>.csv   one row per episode
    <tag>.csv            mean, std, n per (controller, regime, metric)
    results/raw/waits/<controller>__<regime>.npz   per-vehicle waits for the fairness ECDFs
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.config import REGIMES, load_cfg  # noqa: E402
from greenwave.metrics import summarise  # noqa: E402
from greenwave.runner import BASELINES, make_controller, run_episode  # noqa: E402

SUMMARY = ROOT / "results" / "summary"
WAITS = ROOT / "results" / "raw" / "waits"


def eval_seeds(n: int | None = None) -> list[int]:
    lo, hi = load_cfg()["sim"]["seeds"]["eval"]
    seeds = list(range(lo, hi + 1))
    return seeds[:n] if n else seeds


def _episode(task: tuple[str, str, int, int | None]) -> dict[str, Any]:
    key, regime, seed, episode_seconds = task
    import torch

    torch.set_num_threads(1)
    controller = make_controller(key, regime)
    out = run_episode(controller, regime, seed, episode_seconds=episode_seconds, keep_trips=True)
    row: dict[str, Any] = {"controller": key, "regime": regime, "seed": seed, **out["metrics"]}
    trips = out["trips"]
    row["_wait"] = trips["wait"].to_numpy(dtype=np.float32)
    row["_cls"] = trips["cls"].to_numpy(dtype=np.int8)
    return row


def evaluate(
    controllers: list[str],
    regimes: list[str],
    seeds: list[int],
    workers: int,
    tag: str,
    episode_seconds: int | None = None,
    append: bool = False,
) -> pd.DataFrame:
    tasks = [(c, r, s, episode_seconds) for c in controllers for r in regimes for s in seeds]
    rows: list[dict[str, Any]] = []
    waits: dict[tuple[str, str], list[tuple[np.ndarray, np.ndarray]]] = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_episode, t) for t in tasks]
        for i, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            waits.setdefault((row["controller"], row["regime"]), []).append(
                (row.pop("_wait"), row.pop("_cls"))
            )
            rows.append(row)
            if i % 20 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)} episodes  ({time.time() - t0:.0f}s)", flush=True)

    episodes = pd.DataFrame(rows).sort_values(["controller", "regime", "seed"])
    SUMMARY.mkdir(parents=True, exist_ok=True)
    WAITS.mkdir(parents=True, exist_ok=True)
    ep_path = SUMMARY / f"episodes_{tag}.csv"
    if append and ep_path.exists():
        old = pd.read_csv(ep_path)
        old = old[~old["controller"].isin(controllers) | ~old["regime"].isin(regimes)]
        episodes = pd.concat([old, episodes]).sort_values(["controller", "regime", "seed"])
    episodes.to_csv(ep_path, index=False)
    summarise(episodes, ["controller", "regime"]).to_csv(SUMMARY / f"{tag}.csv", index=False)
    for (c, r), parts in waits.items():
        np.savez_compressed(
            WAITS / f"{c}__{r}.npz",
            wait=np.concatenate([p[0] for p in parts]),
            cls=np.concatenate([p[1] for p in parts]),
        )
    return episodes


def finished_jobs() -> list[str]:
    runs = ROOT / "runs"
    return sorted(p.parent.name for p in runs.glob("*/done.flag"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baselines", action="store_true")
    parser.add_argument("--agents", action="store_true")
    parser.add_argument("--controllers", nargs="*", default=[])
    parser.add_argument("--regimes", nargs="*", default=list(REGIMES))
    parser.add_argument("--seeds", type=int, default=None, help="number of eval seeds (default all)")
    parser.add_argument("--workers", type=int, default=7)
    parser.add_argument("--episode-seconds", type=int, default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    controllers = list(args.controllers)
    tag = args.tag or "custom"
    if args.baselines:
        controllers += list(BASELINES)
        tag = args.tag or "baselines"
    if args.agents:
        controllers += [j for j in finished_jobs() if not j.startswith(("smoke", "sweep", "toy"))]
        tag = args.tag or "agents"
    print(f"evaluating {len(controllers)} controllers x {len(args.regimes)} regimes")
    episodes = evaluate(
        controllers, args.regimes, eval_seeds(args.seeds), args.workers, tag,
        args.episode_seconds, args.append,
    )  # fmt: skip
    cols = ["veh_wait", "person_wait", "avg_queue", "throughput", "max_wait", "teleport_pct",
            "depart_delay", "pending"]  # fmt: skip
    print(episodes.groupby(["regime", "controller"])[cols].mean().round(1).to_string())


if __name__ == "__main__":
    main()
