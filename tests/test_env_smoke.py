"""The toy junction runs headless under both back ends and responds to phase commands."""

from __future__ import annotations

import numpy as np
import pytest

from greenwave.env.signal_env import SignalEnv


@pytest.mark.parametrize("libsumo", [True, False])
def test_toy_runs_and_switches(libsumo: bool) -> None:
    env = SignalEnv(network="toy", reward="wait", episode_seconds=300, libsumo=libsumo,
                    label=f"smoke{int(libsumo)}")  # fmt: skip
    try:
        obs, info = env.reset(seed=0, options={"sumo_seed": 7})
        assert obs.shape == env.observation_space.shape
        assert info["phase"] == 0
        seen = {0}
        truncated = False
        steps = 0
        while not truncated:
            action = (env.phase + 1) % 4 if steps % 2 == 0 else env.phase
            obs, reward, terminated, truncated, info = env.step(action)
            assert not terminated
            assert np.isfinite(reward)
            assert env.observation_space.contains(obs)
            seen.add(info["phase"])
            steps += 1
        assert seen == {0, 1, 2, 3}
        stats = info["episode_stats"]
        assert stats["seconds"] == 300
        assert stats["departed"] > 20
    finally:
        env.close()


def test_junction_episode_has_all_classes() -> None:
    env = SignalEnv(regime="peak", episode_seconds=300, label="smoke_j")
    try:
        obs, _ = env.reset(seed=1, options={"sumo_seed": 3})
        assert obs.shape == (29,)
        waited = np.zeros(4)
        truncated = False
        while not truncated:
            _, _, _, truncated, info = env.step(env.action_space.sample())
            waited += info["wait_by_class"]
        assert (waited > 0).all(), "every vehicle class should appear and wait at peak"
    finally:
        env.close()
