"""Max-pressure control (Varaiya 2013), under the same timing constraints as the agent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def phase_pressures(
    queue_in: Sequence[float], queue_out: Sequence[float], movements: Sequence[Sequence[tuple[int, int]]]
) -> np.ndarray:
    """Pressure of a phase = sum over its movements of (incoming queue - outgoing queue), PCU."""
    return np.array(
        [sum(queue_in[i] - queue_out[o] for i, o in phase) for phase in movements], dtype=float
    )


class MaxPressureController:
    name = "max_pressure"
    native_program = None

    def reset(self) -> None:
        return None

    def act(self, obs: Any, info: Mapping[str, Any]) -> int:
        pressure = phase_pressures(info["queue_in"], info["queue_out"], info["movements"])
        best = float(pressure.max())
        current = int(info["phase"])
        # Keep the current phase on ties so equal pressure never costs a yellow.
        if pressure[current] >= best:
            return current
        return int(np.argmax(pressure))
