"""SUMO's built-in gap-based actuated control (minDur 10, maxDur 60, max-gap 3 s)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from greenwave.config import ROOT


class ActuatedController:
    name = "actuated"

    def __init__(self, network: str = "junction") -> None:
        if network == "toy":
            path = ROOT / "network" / "toy" / "tls_actuated_toy.add.xml"
        else:
            path = ROOT / "network" / "tls_actuated.add.xml"
        self.native_program: tuple[str, str] | None = ("actuated", str(path))

    def reset(self) -> None:
        return None

    def act(self, obs: Any, info: Mapping[str, Any]) -> int:
        return 0
