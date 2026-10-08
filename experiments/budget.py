"""Budget planner (spec Section 9): measure simulation speed, estimate every job under
each compute profile, and pick the largest profile that fits the time available.

    python experiments/budget.py --hours 7 --workers 7

Writes runs/plan.json, which experiments/run_queue.py executes.
"""

from __future__ import annotations

import argparse
import heapq
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.config import load_yaml  # noqa: E402
from greenwave.jobs import JobSpec  # noqa: E402
from greenwave.plan import PROFILES, experiment_jobs, job_cores, load_profile, sweep_jobs  # noqa: E402

GRAD_STEP_S = 0.0015  # ~1.5 ms per gradient step on one CPU thread
MIN_MAIN_STEPS = 60_000


def measure_speed(episodes: int = 2) -> dict[str, float]:
    """Random policy on the peak regime, training mode (no tripinfo, no emissions)."""
    os.environ.setdefault("LIBSUMO_AS_TRACI", "1")
    from greenwave.env.signal_env import SignalEnv

    env = SignalEnv(regime="peak", label="budget")
    rng = np.random.default_rng(0)
    steps = 0
    t0 = time.time()
    try:
        for ep in range(episodes):
            env.reset(seed=ep, options={"sumo_seed": ep})
            truncated = False
            while not truncated:
                _, _, _, truncated, _ = env.step(int(rng.integers(4)))
                steps += 1
    finally:
        env.close()
    wall = time.time() - t0
    return {
        "steps_per_s": steps / wall,
        "episode_s": wall / episodes,
        "steps_per_episode": steps / episodes,
    }


def job_minutes(spec: JobSpec, speed: dict[str, float], slowdown: float) -> float:
    """Wall-clock estimate: simulation + gradient steps + validation episodes."""
    interval = (spec.delta or 5) / 5.0
    env_s = spec.steps / speed["steps_per_s"] * interval * slowdown
    n_evals = max(1, spec.steps // spec.eval_every)
    val_s = n_evals * 2 * speed["episode_s"] * slowdown
    if spec.agent == "ppo":
        return (env_s / 3.0 + spec.steps * GRAD_STEP_S * 0.5 + val_s * 3.0) / 60.0
    if spec.agent == "dqn":
        val_s *= 3.0  # validation through TraCI
    return (env_s + spec.steps * GRAD_STEP_S + val_s) / 60.0


def makespan_minutes(jobs: list[tuple[float, int]], workers: int) -> float:
    """Longest-first greedy packing of (minutes, cores) jobs onto `workers` cores."""
    free_at = [0.0] * workers
    heapq.heapify(free_at)
    end = 0.0
    for minutes, cores in sorted(jobs, reverse=True):
        starts = [heapq.heappop(free_at) for _ in range(min(cores, workers))]
        finish = max(starts) + minutes
        for _ in starts:
            heapq.heappush(free_at, finish)
        end = max(end, finish)
    return end


def plan_profile(
    name: str, speed: dict[str, float], workers: int, slowdown: float,
    scale: float = 1.0, drop: tuple[str, ...] = (),
) -> dict[str, Any]:  # fmt: skip
    profile = load_profile(name)
    sweep = sweep_jobs(profile, scale)
    rest = experiment_jobs(profile, scale, drop)
    est_sweep = [(job_minutes(j, speed, slowdown), job_cores(j)) for j in sweep]
    est_rest = [(job_minutes(j, speed, slowdown), job_cores(j)) for j in rest]
    hours = (makespan_minutes(est_sweep, workers) + makespan_minutes(est_rest, workers)) / 60.0
    return {
        "profile": name,
        "scale": scale,
        "dropped_questions": list(drop),
        "n_jobs": len(sweep) + len(rest),
        "total_steps": int(sum(j.steps for j in sweep + rest)),
        "cpu_hours": (sum(m * c for m, c in est_sweep + est_rest)) / 60.0,
        "wall_hours": hours,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=7.0)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2 - 1))
    parser.add_argument("--profile", choices=PROFILES, default=None, help="force a profile")
    parser.add_argument("--slowdown", type=float, default=1.35,
                        help="per-worker slowdown when all cores are busy")  # fmt: skip
    args = parser.parse_args()

    speed = measure_speed()
    print(f"measured {speed['steps_per_s']:.1f} decisions/s, {speed['episode_s']:.1f} s per episode "
          f"({speed['steps_per_episode']:.0f} decisions per episode)")  # fmt: skip

    options = {p: plan_profile(p, speed, args.workers, args.slowdown) for p in PROFILES}
    for p, o in options.items():
        print(f"  {p:5s}: {o['n_jobs']:3d} jobs, {o['total_steps'] / 1e6:5.2f}M steps, "
              f"{o['cpu_hours']:6.1f} CPU-h, ~{o['wall_hours']:5.1f} h on {args.workers} workers")  # fmt: skip

    deviations: list[str] = []
    if args.profile:
        chosen = options[args.profile]
    else:
        fitting = [o for o in (options["full"], options["day"]) if o["wall_hours"] <= args.hours]
        if fitting:
            chosen = fitting[0]
        else:
            # Day does not fit: scale step counts down uniformly, never below 60k main steps,
            # then cut ablation groups in the order given by the spec.
            day_steps = load_profile("day")["main_steps"]
            floor = MIN_MAIN_STEPS / day_steps
            cut_order = load_yaml(ROOT / "configs" / "experiments.yaml")["cut_order"]
            chosen = options["day"]
            drop: tuple[str, ...] = ()
            for extra in [(), *[tuple(cut_order[: i + 1]) for i in range(len(cut_order))]]:
                drop = extra
                scale = max(floor, min(1.0, args.hours / plan_profile(
                    "day", speed, args.workers, args.slowdown, 1.0, drop)["wall_hours"]))  # fmt: skip
                scale = round(scale, 2)
                chosen = plan_profile("day", speed, args.workers, args.slowdown, scale, drop)
                if chosen["wall_hours"] <= args.hours * 1.05:
                    break
            if chosen["scale"] < 1.0:
                deviations.append(
                    f"Step budgets scaled to {chosen['scale']:.0%} of the day profile "
                    f"({int(day_steps * chosen['scale']):,} main steps) to fit {args.hours:g} h."
                )
            if drop:
                deviations.append(f"Ablation groups dropped to fit the time budget: {', '.join(drop)}.")

    plan = {
        **chosen,
        "hours_budget": args.hours,
        "workers": args.workers,
        "speed": speed,
        "slowdown": args.slowdown,
        "options": options,
        "deviations": deviations,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out = ROOT / "runs" / "plan.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"chosen: {chosen['profile']} (scale {chosen['scale']}, ~{chosen['wall_hours']:.1f} h) "
          f"-> {out.relative_to(ROOT)}")  # fmt: skip
    for d in deviations:
        print("  deviation:", d)


if __name__ == "__main__":
    main()
