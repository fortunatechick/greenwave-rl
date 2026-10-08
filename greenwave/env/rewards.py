"""Reward registry (spec Section 4.3).

Every reward has the interface ``reward(prev_info, info) -> float`` where both arguments are
the snapshot dictionaries produced by ``SignalEnv`` at consecutive decision points:

    total_wait      summed accumulated waiting time on incoming lanes, seconds
    wait_by_class   the same split by vehicle class, shape (4,)
    max_wait        longest accumulated wait per approach, shape (n_approaches,)
    queue_in        halting PCU per incoming lane
    queue_out       halting PCU per outgoing lane
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from greenwave.config import class_vector, load_cfg

RewardFn = Callable[[Mapping[str, Any], Mapping[str, Any]], float]

REWARD_NAMES = ("wait", "fair", "passenger_nofair", "vehicle_fair", "queue", "pressure")


def reward_params(**overrides: Any) -> dict[str, Any]:
    """Defaults from configs, with optional overrides: kappa, kappa_q, lam, T, bus_weight."""
    cfg = load_cfg()
    r = cfg["rewards"]
    weights = dict(cfg["demand"]["passenger_weights"])
    if overrides.get("bus_weight") is not None:
        weights["bus"] = float(overrides["bus_weight"])
    # Passenger weights are divided by the mean occupancy of the traffic mix, so the
    # passenger-weighted reward has the scale of the vehicle-count reward and lambda means
    # the same thing in both. Relative weights between classes are unchanged.
    mix = cfg["demand"]["class_mix"]
    mean_occupancy = sum(mix[c] * weights[c] for c in mix)
    params = {
        "kappa": float(r["kappa"]),
        "kappa_q": float(r["kappa_q"]),
        "lam": float(r["lambda"]),
        "T": float(r["T"]),
        "weights": np.asarray(class_vector(weights), dtype=np.float64) / mean_occupancy,
        "mean_occupancy": mean_occupancy,
    }
    for key in ("kappa", "kappa_q", "lam", "T"):
        if overrides.get(key) is not None:
            params[key] = float(overrides[key])
    return params


def fairness_penalty(max_wait: np.ndarray, lam: float, T: float) -> float:
    return lam * max(0.0, float(np.max(max_wait)) - T) / T


def weighted_wait_reduction(
    prev: Mapping[str, Any], cur: Mapping[str, Any], weights: np.ndarray, kappa: float
) -> float:
    delta = np.asarray(prev["wait_by_class"]) - np.asarray(cur["wait_by_class"])
    return float(np.dot(weights, delta)) / kappa


def make_selection_score(
    name: str, gamma: float = 0.99, **overrides: Any
) -> Callable[[Mapping[str, Any], float], float]:
    """Per-decision score used to pick checkpoints (higher is better).

    The undiscounted episode sum of a difference-form reward telescopes to -W_final / kappa,
    which says nothing about the episode. Its discounted objective is equivalent to
    minimising (1 - gamma) * W_t per decision, so that potential form is scored instead.
    Queue and pressure rewards do not telescope and are scored as they are.
    """
    p = reward_params(**overrides)
    kappa, lam, T, weights = p["kappa"], p["lam"], p["T"], p["weights"]

    def score(info: Mapping[str, Any], reward: float) -> float:
        if name in ("queue", "pressure"):
            return reward
        if name == "wait":
            return -(1.0 - gamma) * float(info["total_wait"]) / kappa
        w = np.ones_like(weights) if name == "vehicle_fair" else weights
        value = -(1.0 - gamma) * float(np.dot(w, info["wait_by_class"])) / kappa
        if name in ("fair", "vehicle_fair"):
            value -= fairness_penalty(info["max_wait"], lam, T)
        return value

    return score


def make_reward(name: str, **overrides: Any) -> RewardFn:
    p = reward_params(**overrides)
    kappa, kappa_q, lam, T, weights = p["kappa"], p["kappa_q"], p["lam"], p["T"], p["weights"]
    ones = np.ones_like(weights)

    def wait(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> float:
        return (float(prev["total_wait"]) - float(cur["total_wait"])) / kappa

    def fair(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> float:
        return weighted_wait_reduction(prev, cur, weights, kappa) - fairness_penalty(
            cur["max_wait"], lam, T
        )

    def passenger_nofair(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> float:
        return weighted_wait_reduction(prev, cur, weights, kappa)

    def vehicle_fair(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> float:
        return weighted_wait_reduction(prev, cur, ones, kappa) - fairness_penalty(
            cur["max_wait"], lam, T
        )

    def queue(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> float:
        return -float(np.sum(cur["queue_in"])) / kappa_q

    def pressure(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> float:
        return -abs(float(np.sum(cur["queue_in"])) - float(np.sum(cur["queue_out"]))) / kappa_q

    table: dict[str, RewardFn] = {
        "wait": wait,
        "fair": fair,
        "passenger_nofair": passenger_nofair,
        "vehicle_fair": vehicle_fair,
        "queue": queue,
        "pressure": pressure,
    }
    if name not in table:
        raise KeyError(f"unknown reward '{name}', choose from {REWARD_NAMES}")
    return table[name]
