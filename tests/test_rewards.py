"""Hand-computed reward cases, including the fairness penalty."""

from __future__ import annotations

import numpy as np
import pytest

from greenwave.env.rewards import make_reward, make_selection_score


def snap(wait_by_class, max_wait, queue_in=(0, 0), queue_out=(0, 0)) -> dict:
    wait = np.asarray(wait_by_class, dtype=float)
    return {
        "wait_by_class": wait,
        "total_wait": float(wait.sum()),
        "max_wait": np.asarray(max_wait, dtype=float),
        "queue_in": np.asarray(queue_in, dtype=float),
        "queue_out": np.asarray(queue_out, dtype=float),
    }


# classes: two_wheeler, auto_rickshaw, car, bus -> passenger weights 1.5, 2.5, 2, 40,
# divided by the mean occupancy of the mix: 0.45*1.5 + 0.18*2.5 + 0.30*2 + 0.07*40 = 4.525
OCC = 4.525
OCC_BUS20 = 3.125  # same with a bus weight of 20
PREV = snap([100.0, 50.0, 200.0, 30.0], [40, 40, 40, 40])
CUR = snap([60.0, 50.0, 150.0, 10.0], [50, 20, 30, 80])


def test_wait_reward_is_total_reduction_over_kappa() -> None:
    # (380 - 270) / 100
    assert make_reward("wait")(PREV, CUR) == pytest.approx(1.10)


def test_passenger_weighted_reward_without_penalty() -> None:
    # (1.5*40 + 2.5*0 + 2*50 + 40*20) / 100 = 960 / 100; max wait 80 < T = 90
    assert make_reward("fair")(PREV, CUR) == pytest.approx(9.60 / OCC)
    assert make_reward("passenger_nofair")(PREV, CUR) == pytest.approx(9.60 / OCC)


def test_fairness_penalty_applies_above_threshold() -> None:
    cur = snap([60.0, 50.0, 150.0, 10.0], [50, 20, 30, 135])
    # penalty = 1.0 * (135 - 90) / 90 = 0.5
    assert make_reward("fair")(PREV, cur) == pytest.approx(9.60 / OCC - 0.5)
    assert make_reward("passenger_nofair")(PREV, cur) == pytest.approx(9.60 / OCC)
    # vehicle weighting: 110 / 100 - 0.5
    assert make_reward("vehicle_fair")(PREV, cur) == pytest.approx(1.10 - 0.5)


def test_fairness_overrides() -> None:
    cur = snap([60.0, 50.0, 150.0, 10.0], [50, 20, 30, 135])
    # lambda 4, T 60: 4 * (135 - 60) / 60 = 5.0
    assert make_reward("fair", lam=4.0, T=60.0)(PREV, cur) == pytest.approx(9.60 / OCC - 5.0)
    # bus weight 20: (60 + 100 + 20*20) / 100 = 5.6, penalty 0.5
    assert make_reward("fair", bus_weight=20)(PREV, cur) == pytest.approx(5.60 / OCC_BUS20 - 0.5)


def test_queue_and_pressure() -> None:
    cur = snap([0, 0, 0, 0], [0, 0, 0, 0], queue_in=(12.0, 8.0), queue_out=(5.0, 0.0))
    assert make_reward("queue")(PREV, cur) == pytest.approx(-2.0)
    assert make_reward("pressure")(PREV, cur) == pytest.approx(-1.5)


def test_selection_score_does_not_telescope() -> None:
    score = make_selection_score("fair", gamma=0.99)
    cur = snap([60.0, 50.0, 150.0, 10.0], [50, 20, 30, 135])
    # -(0.01 * (90 + 125 + 300 + 400) / 100) - 0.5
    assert score(cur, 0.0) == pytest.approx(-0.0915 / OCC - 0.5)
    assert make_selection_score("queue")(cur, -2.0) == -2.0


def test_unknown_reward_rejected() -> None:
    with pytest.raises(KeyError):
        make_reward("nope")
