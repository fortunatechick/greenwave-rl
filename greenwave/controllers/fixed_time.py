"""Fixed-time control with Webster's cycle length and green splits (spec Section 6.1)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from greenwave.config import ROOT


@dataclass
class WebsterPlan:
    cycle_optimal: float  # C0 after clamping
    cycle: float  # realised cycle after rounding and clamping the greens
    greens: dict[str, int]  # displayed green per approach, seconds
    y: dict[str, float]
    Y: float
    lost_time: float
    saturation_design: float  # common degree of saturation of the unrounded plan
    saturation: dict[str, float]  # per approach, realised plan


def webster_plan(
    flows_pcu: Mapping[str, float],
    sat_flows: Mapping[str, float],
    yellow: float = 3.0,
    all_red: float = 0.0,
    startup_loss: float = 2.0,
    min_green: float = 10.0,
    max_green: float = 60.0,
    c_min: float = 40.0,
    c_max: float = 150.0,
) -> WebsterPlan:
    """C0 = (1.5 L + 5) / (1 - Y), effective green split proportional to y_i.

    L counts yellow + all-red + start-up loss per phase, so the displayed green of a phase
    is its effective green plus the start-up loss.
    """
    approaches = list(flows_pcu)
    n = len(approaches)
    lost = n * (yellow + all_red + startup_loss)
    y = {a: flows_pcu[a] / sat_flows[a] for a in approaches}
    y_sum = sum(y.values())
    c0 = c_max if y_sum >= 0.99 else (1.5 * lost + 5.0) / (1.0 - y_sum)
    c0 = min(max(c0, c_min), c_max)

    eff_total = c0 - lost
    greens: dict[str, int] = {}
    for a in approaches:
        share = y[a] / y_sum if y_sum > 0 else 1.0 / n
        displayed = eff_total * share + startup_loss
        greens[a] = int(round(min(max(displayed, min_green), max_green)))
    cycle = sum(greens.values()) + n * (yellow + all_red)
    saturation = {
        a: (flows_pcu[a] * cycle) / (sat_flows[a] * max(greens[a] - startup_loss, 1e-9))
        for a in approaches
    }
    return WebsterPlan(
        cycle_optimal=c0,
        cycle=cycle,
        greens=greens,
        y=y,
        Y=y_sum,
        lost_time=lost,
        saturation_design=y_sum * c0 / eff_total,
        saturation=saturation,
    )


def fixed_program_file(plan_regime: str) -> Path:
    return ROOT / "network" / f"tls_fixed_{plan_regime}.add.xml"


class FixedTimeController:
    """Runs a SUMO static program; the environment only observes (passive mode)."""

    def __init__(self, plan_regime: str, name: str = "fixed") -> None:
        self.name = name
        self.native_program: tuple[str, str] | None = (
            f"fixed_{plan_regime}",
            str(fixed_program_file(plan_regime)),
        )

    def reset(self) -> None:
        return None

    def act(self, obs: Any, info: Mapping[str, Any]) -> int:
        return 0
