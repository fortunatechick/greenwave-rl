"""Uniform random phase choice: the sanity floor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np


class RandomPhaseController:
    name = "random"
    native_program = None

    def __init__(self, n_phases: int = 4, seed: int = 0) -> None:
        self.n_phases = n_phases
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def reset(self) -> None:
        self.rng = np.random.default_rng(self.seed)

    def act(self, obs: Any, info: Mapping[str, Any]) -> int:
        return int(self.rng.integers(self.n_phases))
