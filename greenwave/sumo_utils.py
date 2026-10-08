"""Single source of truth for how SUMO is located, started and flagged (spec 5.4)."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def sumo_home() -> Path:
    import sumo  # provided by the eclipse-sumo wheel

    home = Path(sumo.SUMO_HOME)
    os.environ.setdefault("SUMO_HOME", str(home))
    return home


def sumo_binary(name: str = "sumo") -> str:
    exe = name + (".exe" if sys.platform == "win32" else "")
    return str(sumo_home() / "bin" / exe)


def sumo_tool(name: str) -> str:
    return str(sumo_home() / "tools" / name)


# LIBSUMO_AS_TRACI makes `import traci` return libsumo, which would leave no real TraCI
# for the GUI demo or for validation beside a libsumo simulation. The flag is therefore
# read once, remembered under GREENWAVE_BACKEND (inherited by worker processes), and removed.
_flag = os.environ.pop("LIBSUMO_AS_TRACI", None)
if _flag is not None:
    os.environ["GREENWAVE_BACKEND"] = "libsumo" if _flag == "1" else "traci"


def use_libsumo(prefer: bool = True) -> bool:
    """LIBSUMO_AS_TRACI=1 forces libsumo, =0 forces traci, unset uses `prefer`."""
    backend = os.environ.get("GREENWAVE_BACKEND")
    if backend is None:
        return prefer
    return backend == "libsumo"


def build_cmd(
    net: str | Path,
    routes: str | Path,
    additionals: Sequence[str | Path] = (),
    seed: int = 0,
    sublane: bool = True,
    lateral_resolution: float = 0.8,
    tripinfo: str | Path | None = None,
    waiting_time_memory: int = 3600,
    time_to_teleport: int = 300,
    step_length: float = 1.0,
    extra: Sequence[str] = (),
) -> list[str]:
    """SUMO options (without the binary). Tripinfo and the emissions device are only
    attached when `tripinfo` is given, i.e. for evaluation; neither changes dynamics."""
    cmd = [
        "--net-file", str(net),
        "--route-files", str(routes),
        "--step-length", str(step_length),
        "--seed", str(seed),
        "--no-step-log", "true",
        "--no-warnings", "true",
        "--waiting-time-memory", str(waiting_time_memory),
        "--time-to-teleport", str(time_to_teleport),
        "--collision.action", "warn",
    ]  # fmt: skip
    if additionals:
        cmd += ["--additional-files", ",".join(str(a) for a in additionals)]
    if sublane:
        cmd += ["--lateral-resolution", str(lateral_resolution)]
    if tripinfo is not None:
        cmd += [
            "--tripinfo-output", str(tripinfo),
            "--tripinfo-output.write-unfinished", "true",
            "--device.emissions.probability", "1",
        ]  # fmt: skip
    cmd += list(extra)
    return cmd


class SumoHandle:
    """Uniform start / load / close over libsumo (module) and traci (labelled connection).

    `api` exposes the usual domains: api.simulation, api.vehicle, api.lane, api.trafficlight.
    """

    def __init__(self, libsumo: bool = True, gui: bool = False, label: str = "default") -> None:
        self.libsumo = libsumo and not gui
        self.gui = gui
        self.label = label
        self.api: Any = None
        self._started = False

    def start(self, options: list[str]) -> Any:
        if self.libsumo:
            import libsumo

            if self._started:
                libsumo.load(options)
            else:
                libsumo.start([sumo_binary("sumo"), *options])
            self.api = libsumo
        else:
            import traci

            if self._started:
                self.api.load(options)
            else:
                binary = sumo_binary("sumo-gui" if self.gui else "sumo")
                traci.start([binary, *options], label=self.label)
                self.api = traci.getConnection(self.label)
        self._started = True
        return self.api

    def close(self) -> None:
        if not self._started:
            return
        try:
            self.api.close()
        except Exception:  # noqa: BLE001 - closing a dead simulation must not raise
            pass
        self._started = False
        self.api = None
