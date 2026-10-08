"""Toy sanity check (spec 7.1): Double DQN must beat random on the toy junction within
20k steps. Trains runs/toy_ddqn if missing, then compares on three held-out seeds.

    python experiments/toy_sanity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.jobs import JobSpec  # noqa: E402
from greenwave.runner import make_controller, run_episode  # noqa: E402
from greenwave.train import run_job  # noqa: E402

SEEDS = (1000, 1001, 1002)


def main() -> None:
    spec = JobSpec(name="toy_ddqn", network="toy", reward="wait", steps=20_000, eval_every=5_000,
                   group="smoke")  # fmt: skip
    if not (spec.run_dir / "done.flag").exists():
        run_job(spec)

    results: dict[str, list[float]] = {}
    for key in ("toy_ddqn", "random"):
        waits = []
        for seed in SEEDS:
            out = run_episode(make_controller(key, "peak", "toy"), "peak", seed, network="toy")
            waits.append(out["metrics"]["veh_wait"])
        results[key] = waits
        print(f"{key:10s} mean wait per vehicle: {np.mean(waits):7.1f} s  {np.round(waits, 1)}")

    passed = bool(np.mean(results["toy_ddqn"]) < np.mean(results["random"]))
    out_path = ROOT / "results" / "summary" / "toy_sanity.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"passed": passed, "veh_wait": results}, indent=2), encoding="utf-8")
    print("PASS" if passed else "FAIL", "- Double DQN vs random on the toy junction")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
