"""Observation builder (spec Section 4.1).

Layout of the observation vector, for L incoming lanes and A approaches:

    [0, L)        PCU-weighted halting queue per lane / lane capacity, clipped to 1.5
    [L, 2L)       PCU on lane / lane capacity, clipped to 1.5
    [2L, 2L+A)    current green approach, one-hot
    2L+A          time since last change / max green
    (2L+A, end)   longest accumulated wait per approach / T, clipped to WAIT_CLIP
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

LANE_CLIP = 1.5
WAIT_CLIP = 3.0
PCU_LENGTH_M = 7.5  # one PCU of lane capacity per 7.5 m


def obs_size(n_lanes: int, n_approaches: int) -> int:
    return 2 * n_lanes + 2 * n_approaches + 1


def lane_capacity(lengths: Sequence[float]) -> np.ndarray:
    return np.asarray(lengths, dtype=np.float64) / PCU_LENGTH_M


def build_obs(
    snap: Mapping[str, Any],
    capacity: np.ndarray,
    n_approaches: int,
    max_green: float,
    T: float,
    mask: Sequence[str] = (),
) -> np.ndarray:
    """`mask` zeroes feature groups for the state ablations: 'timer', 'max_wait'."""
    queue = np.clip(np.asarray(snap["queue_in"]) / capacity, 0.0, LANE_CLIP)
    density = np.clip(np.asarray(snap["density_in"]) / capacity, 0.0, LANE_CLIP)
    phase = np.zeros(n_approaches)
    phase[int(snap["phase"])] = 1.0
    timer = np.array([0.0 if "timer" in mask else min(snap["green_elapsed"] / max_green, LANE_CLIP)])
    if "max_wait" in mask:
        wait = np.zeros(n_approaches)
    else:
        wait = np.clip(np.asarray(snap["max_wait"]) / T, 0.0, WAIT_CLIP)
    return np.concatenate([queue, density, phase, timer, wait]).astype(np.float32)
