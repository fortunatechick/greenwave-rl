"""Max-pressure picks the right phase on constructed queue states; baselines load."""

from __future__ import annotations

import numpy as np

from greenwave.controllers.actuated import ActuatedController
from greenwave.controllers.max_pressure import MaxPressureController, phase_pressures
from greenwave.env.signal_env import SignalEnv

# Two incoming lanes per phase, three phases; lane i of phase p feeds outgoing lane p.
MOVEMENTS = [[(0, 0), (1, 0)], [(2, 1), (3, 1)], [(4, 2), (5, 2)]]


def info(queue_in, queue_out, phase) -> dict:
    return {"queue_in": np.asarray(queue_in, float), "queue_out": np.asarray(queue_out, float),
            "movements": MOVEMENTS, "phase": phase}  # fmt: skip


def test_pressure_values() -> None:
    p = phase_pressures([4, 2, 9, 1, 0, 3], [1, 0, 2], MOVEMENTS)
    # (4-1)+(2-1)=4, (9-0)+(1-0)=10, (0-2)+(3-2)=-1
    assert p.tolist() == [4.0, 10.0, -1.0]


def test_picks_largest_pressure() -> None:
    ctrl = MaxPressureController()
    assert ctrl.act(None, info([4, 2, 9, 1, 0, 3], [1, 0, 2], phase=0)) == 1


def test_downstream_queue_reduces_pressure() -> None:
    ctrl = MaxPressureController()
    # Phase 1 has the longest queue, but its exit is blocked.
    assert ctrl.act(None, info([4, 2, 9, 1, 0, 3], [0, 8, 0], phase=2)) == 0


def test_tie_keeps_current_phase() -> None:
    ctrl = MaxPressureController()
    assert ctrl.act(None, info([3, 3, 3, 3, 3, 3], [0, 0, 0], phase=2)) == 2


def test_actuated_program_loads_and_cycles() -> None:
    ctrl = ActuatedController("toy")
    env = SignalEnv(network="toy", reward="wait", episode_seconds=240, label="act",
                    native_program=ctrl.native_program)  # fmt: skip
    try:
        obs, inf = env.reset(seed=0, options={"sumo_seed": 5})
        phases = {inf["phase"]}
        truncated = False
        while not truncated:
            obs, _, _, truncated, inf = env.step(ctrl.act(obs, inf))
            phases.add(inf["phase"])
        assert len(phases) == 4
        assert env.api.trafficlight.getProgram(env.tls) == "actuated"
    finally:
        env.close()
