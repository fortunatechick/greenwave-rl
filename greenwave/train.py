"""Shared training entry point.

    python -m greenwave.train --config runs/<job>/config.json
    python -m greenwave.train --name toy_ddqn --network toy --reward wait --steps 20000

Writes to runs/<job>/: config.json, curve.csv, best.pt | best.zip, tb/, result.json, done.flag
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from greenwave.config import dr_pool_files, load_cfg, route_path
from greenwave.env.rewards import make_selection_score
from greenwave.env.signal_env import SignalEnv
from greenwave.jobs import JobSpec

CURVE_FIELDS = ["step", "val_score", "val_reward", "val_avg_queue", "train_reward", "epsilon", "wall_s"]


def validation_cases(spec: JobSpec) -> list[tuple[int, str]]:
    """(sumo seed, route file) pairs: seeds 900 and 901, never used for training or eval."""
    seeds = load_cfg()["sim"]["seeds"]["validation"]
    if spec.regime == "dr":
        pool = dr_pool_files()
        return [(s, pool[i]) for i, s in enumerate(seeds)]
    return [(s, str(route_path(spec.regime, spec.network))) for s in seeds]


def validate(
    env: SignalEnv, act: Callable[[np.ndarray], int], spec: JobSpec
) -> dict[str, float]:
    """Greedy episodes on the validation seeds; returns the time-weighted selection score."""
    score_fn = make_selection_score(spec.reward, **spec.reward_overrides())
    scores, rewards, queues = [], [], []
    for seed, route in validation_cases(spec):
        obs, _ = env.reset(options={"sumo_seed": seed, "route_file": route})
        weighted, seconds, truncated = 0.0, 0.0, False
        info: dict[str, Any] = {}
        while not truncated:
            obs, reward, _, truncated, info = env.step(act(obs))
            weighted += score_fn(info, reward) * info["dt"]
            seconds += info["dt"]
        scores.append(weighted / max(seconds, 1.0))
        rewards.append(info["episode_stats"]["episode_reward"])
        queues.append(info["episode_stats"]["avg_queue"])
    return {
        "val_score": float(np.mean(scores)),
        "val_reward": float(np.mean(rewards)),
        "val_avg_queue": float(np.mean(queues)),
    }


class CurveLog:
    def __init__(self, run_dir: Path) -> None:
        self.path = run_dir / "curve.csv"
        with open(self.path, "w", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, CURVE_FIELDS).writeheader()

    def add(self, row: dict[str, float]) -> None:
        with open(self.path, "a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, CURVE_FIELDS).writerow({k: row.get(k, "") for k in CURVE_FIELDS})


def train_ddqn(spec: JobSpec) -> dict[str, float]:
    import torch
    from torch.utils.tensorboard import SummaryWriter

    from greenwave.agents.dqn_scratch import DDQNConfig, DoubleDQN

    torch.set_num_threads(1)
    hp = dict(load_cfg()["train"]["ddqn"])
    hp["hidden"] = tuple(hp["hidden"])
    cfg = DDQNConfig(**hp, smdp_discount=spec.smdp_discount, base_dt=float(spec.delta or 5))
    run_dir = spec.run_dir
    env = SignalEnv(**spec.env_kwargs())
    agent = DoubleDQN(env.observation_space.shape[0], env.action_space.n, cfg, seed=spec.seed)
    writer = SummaryWriter(str(run_dir / "tb"))
    curve = CurveLog(run_dir)

    best = -np.inf
    recent: deque[float] = deque(maxlen=5)
    next_eval = spec.eval_every
    t0 = time.time()
    obs, _ = env.reset(seed=spec.seed)
    loss = 0.0
    try:
        for step in range(1, spec.steps + 1):
            eps = agent.epsilon(step, spec.steps)
            action = agent.act(obs, eps)
            next_obs, reward, terminated, truncated, info = env.step(action)
            agent.buffer.add(obs, action, reward, next_obs, terminated, info["dt"])
            obs = next_obs
            if step >= cfg.learning_starts and step % cfg.train_freq == 0:
                loss = agent.update()
            if step % cfg.target_update == 0:
                agent.sync_target()
            if step % 1000 == 0:
                writer.add_scalar("train/loss", loss, step)
                writer.add_scalar("train/epsilon", eps, step)

            if terminated or truncated:
                recent.append(info["episode_stats"]["episode_reward"])
                writer.add_scalar("train/episode_reward", recent[-1], step)
                writer.add_scalar("train/avg_queue", info["episode_stats"]["avg_queue"], step)
                # libsumo allows one simulation per process, so validation reuses the
                # training env at the first episode boundary after each eval interval.
                if step >= next_eval or step == spec.steps:
                    val = validate(env, agent.greedy, spec)
                    row = {"step": step, **val, "train_reward": float(np.mean(recent)),
                           "epsilon": eps, "wall_s": time.time() - t0}  # fmt: skip
                    curve.add(row)
                    for key, value in val.items():
                        writer.add_scalar(f"eval/{key}", value, step)
                    if val["val_score"] > best:
                        best = val["val_score"]
                        agent.save(run_dir / "best.pt", {"step": step, **val})
                    next_eval = (step // spec.eval_every + 1) * spec.eval_every
                obs, _ = env.reset()

        if not (run_dir / "best.pt").exists() or next_eval <= spec.steps:
            val = validate(env, agent.greedy, spec)
            curve.add({"step": spec.steps, **val, "train_reward": float(np.mean(recent or [0.0])),
                       "epsilon": cfg.eps_end, "wall_s": time.time() - t0})  # fmt: skip
            if val["val_score"] > best:
                best = val["val_score"]
                agent.save(run_dir / "best.pt", {"step": spec.steps, **val})
    finally:
        env.close()
        writer.close()
    return {"best_val_score": float(best), "wall_s": time.time() - t0}


def run_job(spec: JobSpec) -> dict[str, float]:
    run_dir = spec.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(spec.to_json(), encoding="utf-8")
    np.random.seed(spec.seed)
    if spec.agent == "ddqn":
        result = train_ddqn(spec)
    elif spec.agent in ("dqn", "ppo"):
        from greenwave.agents.train_sb3 import train_sb3

        result = train_sb3(spec)
    else:
        raise ValueError(f"unknown agent {spec.agent}")
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (run_dir / "done.flag").write_text("done\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="path to a JobSpec json")
    parser.add_argument("--name")
    parser.add_argument("--agent", default="ddqn", choices=["ddqn", "dqn", "ppo"])
    parser.add_argument("--regime", default="peak")
    parser.add_argument("--reward", default="fair")
    parser.add_argument("--network", default="junction")
    parser.add_argument("--steps", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eval-every", type=int, default=10_000)
    parser.add_argument("--smdp-discount", action="store_true")
    args = parser.parse_args()
    if args.config:
        spec = JobSpec.load(args.config)
    else:
        name = args.name or f"{args.agent}_{args.reward}__{args.regime}__s{args.seed}"
        spec = JobSpec(
            name=name, agent=args.agent, regime=args.regime, reward=args.reward,
            network=args.network, steps=args.steps, seed=args.seed, eval_every=args.eval_every,
            smdp_discount=args.smdp_discount, group="manual",
        )  # fmt: skip
    result = run_job(spec)
    print(f"{spec.name}: best validation score {result['best_val_score']:.4f} "
          f"in {result['wall_s'] / 60:.1f} min")  # fmt: skip


if __name__ == "__main__":
    main()
