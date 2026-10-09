"""A back-of-envelope corridor comparison for each demo scene.

    python experiments/corridor_estimate.py

Picture a straight 100 km road with 10 signals, one every 10 km, and a speed cap of 100 km/h.
Free flow takes 60 minutes. A car driving it is delayed once per signal; this script takes
that delay from our junction: the mean time loss of cars going straight through, measured
on the evaluation seeds for both controllers of a scene. Trip time = 60 min + 10 x delay.

It is an extrapolation, not a corridor simulation: every signal is assumed to behave like
our isolated junction under the scene's demand, with no coordination between signals, and
the per-signal delay was measured at a 50 km/h limit. "Major road" is the E-W through
movement (3 lanes), "minor road" the N-S through movement (2 lanes).
"""

from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.evaluate import eval_seeds  # noqa: E402
from experiments.record_replay import SCENES  # noqa: E402
from greenwave.aggregate import write_json  # noqa: E402
from greenwave.jobs import family_jobs  # noqa: E402
from greenwave.runner import BASELINES, make_controller, run_episode  # noqa: E402
from greenwave.tls import THROUGH_OF  # noqa: E402

LENGTH_KM, SIGNALS, SPEED_KMH = 100.0, 10, 100.0
FREE_FLOW_S = LENGTH_KM / SPEED_KMH * 3600.0
ROADS = {"major": ("E", "W"), "minor": ("N", "S")}
CAR = 2  # class index


def _episode(task: tuple[str, str, int]) -> dict[str, Any]:
    key, regime, seed = task
    import torch

    torch.set_num_threads(1)
    trips = run_episode(make_controller(key, regime), regime, seed, keep_trips=True)["trips"]
    through = trips[(trips["cls"] == CAR) & (trips["dest"] == trips["approach"].map(THROUGH_OF))]
    row: dict[str, Any] = {"job": key, "regime": regime, "seed": seed}
    for road, origins in ROADS.items():
        sel = through[through["approach"].isin(origins)]
        row[road] = float(sel["time_loss"].mean()) if len(sel) else np.nan
    return row


def jobs_of(key: str) -> list[str]:
    return [key] if key in BASELINES else family_jobs(key)


def main() -> None:
    seeds = eval_seeds()
    tasks = sorted({(job, scene["regime"], seed) for scene in SCENES.values() for side in ("left", "right")
                    for job in jobs_of(scene[side]) for seed in seeds})  # fmt: skip
    print(f"{len(tasks)} episodes")
    with ProcessPoolExecutor(max_workers=7) as pool:
        episodes = pd.DataFrame(list(pool.map(_episode, tasks, chunksize=2)))

    def per_seed(key: str, regime: str, road: str) -> pd.Series:
        """Delay per signal for each evaluation seed, averaged over a family's training seeds."""
        sel = episodes[episodes["job"].isin(jobs_of(key)) & (episodes["regime"] == regime)]
        return sel.groupby("seed")[road].mean()

    scenes: dict[str, Any] = {}
    for name, scene in SCENES.items():
        roads = {}
        for road in ROADS:
            left = per_seed(scene["left"], scene["regime"], road)
            right = per_seed(scene["right"], scene["regime"], road)
            saved = (left - right) * SIGNALS  # paired: both sides saw the same traffic seeds
            roads[road] = {
                "left_delay_s": float(left.mean()),
                "right_delay_s": float(right.mean()),
                "left_trip_s": FREE_FLOW_S + SIGNALS * float(left.mean()),
                "right_trip_s": FREE_FLOW_S + SIGNALS * float(right.mean()),
                "saved_s": float(saved.mean()),
                "saved_std_s": float(saved.std(ddof=1)),
                "n_seeds": int(len(saved)),
            }
            print(f"{name:15s} {road:5s} left {left.mean():6.1f} s  right {right.mean():6.1f} s per signal  "
                  f"-> right saves {saved.mean():+7.1f} +- {saved.std(ddof=1):.1f} s in total")  # fmt: skip
        scenes[name] = {"regime": scene["regime"], "left": scene["left"], "right": scene["right"], "roads": roads}

    write_json("corridor.json", {
        "length_km": LENGTH_KM, "signals": SIGNALS, "speed_kmh": SPEED_KMH, "free_flow_s": FREE_FLOW_S,
        "vehicle": "car, straight through", "scenes": scenes,
    })  # fmt: skip


if __name__ == "__main__":
    main()
