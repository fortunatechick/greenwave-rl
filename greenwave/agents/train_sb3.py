"""Stable-Baselines3 comparison agents (spec Section 7.2): vanilla DQN and PPO, on the
identical environment and reward as the scratch Double DQN."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import numpy as np

from greenwave.config import load_cfg
from greenwave.env.signal_env import SignalEnv
from greenwave.jobs import JobSpec


def _make_env(kwargs: dict[str, Any], seed: int) -> Callable[[], Any]:
    def thunk() -> Any:
        from stable_baselines3.common.monitor import Monitor

        env = SignalEnv(**kwargs)
        env.reset(seed=seed)
        return Monitor(env)

    return thunk


def train_sb3(spec: JobSpec) -> dict[str, float]:
    import torch
    from stable_baselines3 import DQN, PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

    from greenwave.train import CurveLog, validate

    torch.set_num_threads(1)
    hp = load_cfg()["train"]
    run_dir = spec.run_dir
    kwargs = spec.env_kwargs()
    t0 = time.time()

    if spec.agent == "dqn":
        h = dict(hp["sb3_dqn"])
        net_arch = h.pop("net_arch")
        venv = DummyVecEnv([_make_env(kwargs, spec.seed)])
        model = DQN(
            "MlpPolicy", venv, policy_kwargs={"net_arch": net_arch}, seed=spec.seed,
            tensorboard_log=str(run_dir / "tb"), device="cpu", verbose=0, **h,
        )  # fmt: skip
    else:
        h = dict(hp["ppo"])
        net_arch = h.pop("net_arch")
        n_envs = h.pop("n_envs")
        venv = SubprocVecEnv(
            [_make_env(kwargs, spec.seed * 100 + i) for i in range(n_envs)], start_method="spawn"
        )
        model = PPO(
            "MlpPolicy", venv, policy_kwargs={"net_arch": net_arch}, seed=spec.seed,
            tensorboard_log=str(run_dir / "tb"), device="cpu", verbose=0, **h,
        )  # fmt: skip

    # The training simulations hold libsumo in their processes; validation runs through a
    # separate TraCI simulation so it never disturbs a training episode.
    eval_kwargs = {**kwargs, "libsumo": False, "label": f"val_{spec.name}"}
    eval_env = SignalEnv(**eval_kwargs)
    curve = CurveLog(run_dir)
    state = {"best": -np.inf, "next": spec.eval_every, "last": -1}

    def greedy(obs: np.ndarray) -> int:
        action, _ = model.predict(obs, deterministic=True)
        return int(action)

    def evaluate(step: int) -> None:
        if step == state["last"]:
            return
        state["last"] = step
        val = validate(eval_env, greedy, spec)
        rewards = [ep["r"] for ep in model.ep_info_buffer] if model.ep_info_buffer else [0.0]
        curve.add({"step": step, **val, "train_reward": float(np.mean(rewards[-5:])),
                   "epsilon": float(getattr(model, "exploration_rate", 0.0)),
                   "wall_s": time.time() - t0})  # fmt: skip
        for key, value in val.items():
            model.logger.record(f"eval/{key}", value)
        if val["val_score"] > state["best"]:
            state["best"] = val["val_score"]
            model.save(str(run_dir / "best"))

    class EvalCallback(BaseCallback):
        def _on_step(self) -> bool:
            if self.num_timesteps >= state["next"]:
                evaluate(self.num_timesteps)
                state["next"] = (self.num_timesteps // spec.eval_every + 1) * spec.eval_every
            return True

    try:
        model.learn(total_timesteps=spec.steps, callback=EvalCallback(), progress_bar=False)
        evaluate(int(model.num_timesteps))
    finally:
        venv.close()
        eval_env.close()
    return {"best_val_score": float(state["best"]), "wall_s": time.time() - t0}
