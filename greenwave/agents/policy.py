"""Frozen trained policies behind the controller interface (epsilon = 0, deterministic)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from greenwave.jobs import JobSpec, find_checkpoint


class AgentController:
    native_program = None

    def __init__(self, job_name: str) -> None:
        cfg_path, weights = find_checkpoint(job_name)
        self.spec = JobSpec.load(cfg_path)
        self.name = job_name
        self.env_kwargs = self.spec.env_kwargs(training=False)
        self._sb3 = None
        self._ddqn = None
        if self.spec.agent == "ddqn":
            from greenwave.agents.dqn_scratch import DoubleDQN

            self._ddqn = DoubleDQN.load(weights)
        else:
            from stable_baselines3 import DQN, PPO

            cls = DQN if self.spec.agent == "dqn" else PPO
            self._sb3 = cls.load(str(weights), device="cpu")

    def reset(self) -> None:
        return None

    def act(self, obs: np.ndarray, info: Mapping[str, Any]) -> int:
        if self._ddqn is not None:
            return self._ddqn.greedy(obs)
        action, _ = self._sb3.predict(obs, deterministic=True)
        return int(action)
