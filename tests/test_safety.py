"""Safety constraints are enforced by the environment whatever the policy does.

The check reads the signal state SUMO actually applied each second, not the env's own
bookkeeping: 100 random-policy episodes of 600 s, never a green shorter than min_green,
always exactly 3 s of yellow on a change, never a green longer than max_green.
"""

from __future__ import annotations

import os

import numpy as np

from greenwave.env.signal_env import SignalEnv

EPISODES = int(os.environ.get("GREENWAVE_SAFETY_EPISODES", "100"))


def runs_of(trace: list[tuple[str, int | None]]) -> list[tuple[str, int | None, int]]:
    """Collapse per-second (colour, approach) samples into (colour, approach, duration)."""
    out: list[tuple[str, int | None, int]] = []
    for colour, approach in trace:
        if out and out[-1][0] == colour and out[-1][1] == approach:
            out[-1] = (colour, approach, out[-1][2] + 1)
        else:
            out.append((colour, approach, 1))
    return out


def classify(env: SignalEnv, state: str) -> tuple[str, int | None]:
    active = env.layout.phase_of_state(state)
    if active is not None:
        return "G", active
    for a, link in enumerate(env.layout.through_link):
        if state[link] == "y":
            return "y", a
    return "r", None


def test_random_policy_never_violates_timing() -> None:
    env = SignalEnv(network="toy", reward="wait", episode_seconds=600, trace_signal=True,
                    label="safety")  # fmt: skip
    rng = np.random.default_rng(0)
    greens_seen: set[int] = set()
    try:
        for episode in range(EPISODES):
            env.reset(seed=episode, options={"sumo_seed": episode})
            truncated = False
            # Bias some episodes towards holding the phase so max_green is exercised.
            hold = 0.9 if episode % 4 == 0 else 0.0
            while not truncated:
                action = env.phase if rng.random() < hold else int(rng.integers(4))
                _, _, _, truncated, _ = env.step(action)
            runs = runs_of([classify(env, s) for s in env.signal_trace])
            last = len(runs) - 1
            for i, (colour, approach, duration) in enumerate(runs):
                if colour == "G":
                    assert duration <= env.max_green, f"green of {duration}s exceeds max"
                    if i != last:
                        greens_seen.add(duration)
                        assert duration >= env.min_green, f"green of {duration}s below min"
                        assert runs[i + 1][:2] == ("y", approach), "green must end in its yellow"
                if colour == "y" and i != last:
                    assert duration == env.yellow, f"yellow lasted {duration}s"
                    assert runs[i + 1][0] == "G" and runs[i + 1][1] != approach
    finally:
        env.close()
    assert env.max_green in greens_seen, "max green was never reached, test is too weak"
    assert env.min_green in greens_seen
    assert all(g % env.delta == 0 for g in greens_seen), "greens must sit on the 5 s grid"


def test_forced_switch_goes_to_longest_wait() -> None:
    env = SignalEnv(network="toy", reward="wait", episode_seconds=400, label="forced")
    try:
        env.reset(seed=0, options={"sumo_seed": 1})
        forced_seen = False
        truncated = False
        while not truncated:
            before = env.phase
            _, _, _, truncated, info = env.step(env.phase)  # always ask to extend
            if info["forced"]:
                forced_seen = True
                assert info["phase"] != before
                assert info["green_elapsed"] == env.min_green
        assert forced_seen
        assert env.stats["forced_switches"] >= 3
    finally:
        env.close()
