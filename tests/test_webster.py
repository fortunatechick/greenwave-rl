"""Webster's method on a hand-worked example."""

from __future__ import annotations

import pytest

from greenwave.controllers.fixed_time import webster_plan


def test_hand_worked_two_phase_example() -> None:
    # y = 600/1800 = 1/3 and 300/1800 = 1/6, Y = 0.5
    # L = 2 * (3 + 0 + 2) = 10 s, C0 = (1.5*10 + 5) / (1 - 0.5) = 40 s
    # effective green 30 s split 2:1 -> 20 s and 10 s, displayed = effective + 2 s start-up
    plan = webster_plan({"A": 600, "B": 300}, {"A": 1800, "B": 1800}, yellow=3, all_red=0,
                        startup_loss=2, min_green=5, max_green=60)  # fmt: skip
    assert plan.Y == pytest.approx(0.5)
    assert plan.lost_time == pytest.approx(10.0)
    assert plan.cycle_optimal == pytest.approx(40.0)
    assert plan.greens == {"A": 22, "B": 12}
    assert plan.cycle == pytest.approx(40.0)
    # x = Y * C / (C - L) = 0.5 * 40 / 30
    assert plan.saturation_design == pytest.approx(2 / 3)
    assert plan.saturation["A"] == pytest.approx(600 * 40 / (1800 * 20))


def test_cycle_and_green_clamps() -> None:
    light = webster_plan({"A": 50, "B": 50}, {"A": 1800, "B": 1800}, min_green=10)
    assert light.cycle_optimal == 40.0  # clamped up from (20) / (1 - 0.056)
    assert all(g >= 10 for g in light.greens.values())

    heavy = webster_plan({"A": 900, "B": 850}, {"A": 1800, "B": 1800})
    assert heavy.cycle_optimal == 150.0  # (20) / (1 - 0.972) is far above the cap
    assert all(g <= 60 for g in heavy.greens.values())


def test_peak_demand_is_calibrated_to_target_saturation() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from demand.generate import calibrate_peak, plan_for
    from greenwave.config import load_cfg

    cfg = load_cfg()
    plan = plan_for(cfg, calibrate_peak(cfg))
    assert plan.saturation_design == pytest.approx(cfg["demand"]["target_saturation"], abs=0.01)
    assert 40 <= plan.cycle <= 150
