"""Run one episode of any controller through SignalEnv and compute its metrics."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from greenwave.config import ROOT
from greenwave.controllers.actuated import ActuatedController
from greenwave.controllers.fixed_time import FixedTimeController
from greenwave.controllers.max_pressure import MaxPressureController
from greenwave.controllers.random_phase import RandomPhaseController
from greenwave.env.signal_env import SignalEnv
from greenwave.metrics import episode_metrics, parse_tripinfo

BASELINES = ("fixed_matched", "fixed_peak", "actuated", "max_pressure", "random")


def make_controller(key: str, regime: str, network: str = "junction") -> Any:
    """Baselines by name; anything else is the name of a trained job."""
    if key == "fixed_matched":
        return FixedTimeController(regime, name=key)
    if key == "fixed_peak":
        return FixedTimeController("peak", name=key)
    if key == "actuated":
        return ActuatedController(network)
    if key == "max_pressure":
        return MaxPressureController()
    if key == "random":
        return RandomPhaseController()
    from greenwave.agents.policy import AgentController

    return AgentController(key)


def run_episode(
    controller: Any,
    regime: str,
    sumo_seed: int,
    *,
    network: str = "junction",
    env_kwargs: dict[str, Any] | None = None,
    episode_seconds: int | None = None,
    with_tripinfo: bool = True,
    keep_trips: bool = False,
    hooks: Sequence[Callable[[SignalEnv], None]] = (),
    step_hook: Callable[[SignalEnv, dict[str, Any]], None] | None = None,
    label: str = "default",
    libsumo: bool | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"network": network, "reward": "fair"}
    kwargs.update(getattr(controller, "env_kwargs", None) or {})
    kwargs.update(env_kwargs or {})
    kwargs.update(regime=regime, episode_seconds=episode_seconds, label=label, libsumo=libsumo)

    tripinfo: Path | None = None
    if with_tripinfo:
        raw = ROOT / "results" / "raw" / "tripinfo"
        raw.mkdir(parents=True, exist_ok=True)
        tripinfo = raw / f"{uuid.uuid4().hex}.xml"

    env = SignalEnv(native_program=controller.native_program, tripinfo=tripinfo, **kwargs)
    env.second_hooks.extend(hooks)
    stats: dict[str, float] = {}
    try:
        controller.reset()
        obs, info = env.reset(seed=sumo_seed, options={"sumo_seed": sumo_seed})
        truncated = False
        while not truncated:
            obs, _, _, truncated, info = env.step(controller.act(obs, info))
            if step_hook is not None:
                step_hook(env, info)
        stats = info["episode_stats"]
    finally:
        env.close()

    result: dict[str, Any] = {"stats": stats}
    if tripinfo is not None:
        trips = parse_tripinfo(tripinfo)
        tripinfo.unlink(missing_ok=True)
        result["metrics"] = episode_metrics(trips, stats)
        if keep_trips:
            result["trips"] = trips
    return result
