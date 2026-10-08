"""Gymnasium environment for one signalised junction (spec Section 4).

Timing state machine, enforced here and never learned:

    GREEN(p) --agent picks p-->  GREEN(p) for delta more seconds
    GREEN(p) --agent picks q-->  YELLOW(p) 3 s --> [ALL_RED] --> GREEN(q) for min_green

The agent is only queried at legal decision points. When a green reaches max_green the
environment forces a switch to the approach with the longest current wait without asking.

Passive mode (`native_program`): a SUMO program (fixed-time or actuated) drives the signal
and the environment only observes, so those baselines share the metric code.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np

from greenwave.config import (
    CLASSES,
    CODE_INDEX,
    class_vector,
    load_cfg,
    net_path,
    route_path,
    vtypes_path,
)
from greenwave.env.rewards import RewardFn, make_reward, reward_params
from greenwave.env.state import build_obs, lane_capacity, obs_size
from greenwave.sumo_utils import SumoHandle, build_cmd, use_libsumo
from greenwave.tls import TlsLayout, read_layout

HALT_SPEED = 0.1  # m/s, SUMO's own halting threshold

_LAYOUT_CACHE: dict[tuple[str, bool], TlsLayout] = {}


def get_layout(network: str = "junction") -> TlsLayout:
    cfg = load_cfg()
    free_left = bool(cfg["junction"]["free_left"]) if network == "junction" else False
    key = (network, free_left)
    if key not in _LAYOUT_CACHE:
        _LAYOUT_CACHE[key] = read_layout(
            net_path(network), cfg["junction"]["approaches"], free_left, cfg["junction"]["tls_id"]
        )
    return _LAYOUT_CACHE[key]


class SignalEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        network: str = "junction",
        regime: str = "peak",
        route_files: Sequence[str | Path] | None = None,
        reward: str = "fair",
        reward_overrides: dict[str, Any] | None = None,
        delta: int | None = None,
        sublane: bool | None = None,
        obs_mask: Sequence[str] = (),
        native_program: tuple[str, str] | None = None,
        seed_range: tuple[int, int] | None = None,
        episode_seconds: int | None = None,
        tripinfo: str | Path | None = None,
        libsumo: bool | None = None,
        gui: bool = False,
        label: str = "default",
        trace_signal: bool = False,
        extra_sumo_args: Sequence[str] = (),
    ) -> None:
        super().__init__()
        cfg = load_cfg()
        sim = cfg["sim"]
        self.network = network
        self.regime = regime
        self.layout = get_layout(network)
        self.tls = self.layout.tls_id
        self.net_file = net_path(network)
        self.route_files = [str(r) for r in (route_files or [route_path(regime, network)])]
        self.sublane = bool(sim["sublane"]) if sublane is None else sublane
        self.vtypes = vtypes_path() if self.sublane else vtypes_path().with_name(
            "vtypes_nosublane.add.xml"
        )

        self.delta = int(delta or sim["decision_interval"])
        self.min_green = int(sim["min_green"])
        self.max_green = int(sim["max_green"])
        self.yellow = int(sim["yellow"])
        self.all_red = int(sim["all_red"])
        self.horizon = int(episode_seconds or sim["episode_seconds"])
        self.sim_cfg = sim
        self.seed_range = seed_range or tuple(sim["seeds"]["train"])
        self.tripinfo = tripinfo
        self.native_program = native_program
        self.trace_signal = trace_signal
        self.extra_sumo_args = list(extra_sumo_args)

        self.reward_name = reward
        self.reward_overrides = dict(reward_overrides or {})
        self.reward_fn: RewardFn = make_reward(reward, **self.reward_overrides)
        self.T = reward_params(**self.reward_overrides)["T"]
        self.obs_mask = tuple(obs_mask)

        self.pcu = np.asarray(class_vector(cfg["demand"]["pcu"]))
        self.n_app = self.layout.n_phases
        self.n_lanes = len(self.layout.in_lanes)
        self.capacity = lane_capacity(self.layout.lane_length)
        self.observation_space = gym.spaces.Box(
            low=0.0, high=3.0, shape=(obs_size(self.n_lanes, self.n_app),), dtype=np.float32
        )
        self.action_space = gym.spaces.Discrete(self.n_app)

        prefer = use_libsumo(True) if libsumo is None else libsumo
        self.handle = SumoHandle(libsumo=prefer, gui=gui, label=label)
        self.api: Any = None
        self.second_hooks: list[Callable[[SignalEnv], None]] = []

        self.t = 0
        self.phase = 0
        self.green_elapsed = 0
        self.signal_colour = "G"
        self.snap: dict[str, Any] = {}
        self.signal_trace: list[str] = []
        self._reset_counters()

    # ------------------------------------------------------------------ lifecycle
    def _reset_counters(self) -> None:
        self.stats = {
            "teleports": 0,
            "collisions": 0,
            "forced_switches": 0,
            "switches": 0,
            "departed": 0,
            "arrived": 0,
            "halting_seconds": 0.0,
            "decisions": 0,
            "episode_reward": 0.0,
        }

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        options = options or {}
        lo, hi = self.seed_range
        sumo_seed = int(options.get("sumo_seed", self.np_random.integers(lo, hi + 1)))
        routes = options.get("route_file") or self.route_files[
            int(self.np_random.integers(len(self.route_files)))
        ]
        additionals: list[str | Path] = [self.vtypes]
        if self.native_program:
            additionals.append(self.native_program[1])
        cmd = build_cmd(
            self.net_file,
            routes,
            additionals,
            seed=sumo_seed,
            sublane=self.sublane,
            lateral_resolution=self.sim_cfg["lateral_resolution"],
            tripinfo=self.tripinfo,
            waiting_time_memory=self.sim_cfg["waiting_time_memory"],
            time_to_teleport=self.sim_cfg["time_to_teleport"],
            step_length=self.sim_cfg["step_length"],
            extra=self.extra_sumo_args,
        )
        self.api = self.handle.start(cmd)
        self.sumo_seed = sumo_seed
        self.t = 0
        self.phase = 0
        self.green_elapsed = 0
        self.signal_trace = []
        self._reset_counters()

        if self.native_program:
            self.api.trafficlight.setProgram(self.tls, self.native_program[0])
            self._advance(self.delta)
        else:
            self._set_state(self.layout.green[0], "G")
            self._advance(self.min_green)
            self.green_elapsed = self.min_green
        self.snap = self._snapshot()
        return self._obs(), dict(self.snap)

    def close(self) -> None:
        self.handle.close()
        self.api = None

    # ------------------------------------------------------------------ stepping
    def _set_state(self, state: str, colour: str) -> None:
        self.api.trafficlight.setRedYellowGreenState(self.tls, state)
        self.signal_colour = colour

    def _advance(self, seconds: int) -> None:
        api, sim, lane = self.api, self.api.simulation, self.api.lane
        stats = self.stats
        for _ in range(int(seconds)):
            if self.t >= self.horizon:
                return
            api.simulationStep()
            self.t += 1
            stats["teleports"] += sim.getStartingTeleportNumber()
            stats["collisions"] += sim.getCollidingVehiclesNumber()
            stats["departed"] += sim.getDepartedNumber()
            stats["arrived"] += sim.getArrivedNumber()
            halting = 0
            for ln in self.layout.in_lanes:
                halting += lane.getLastStepHaltingNumber(ln)
            stats["halting_seconds"] += halting
            self.halting_now = halting
            if self.native_program or self.trace_signal:
                state = api.trafficlight.getRedYellowGreenState(self.tls)
                if self.trace_signal:
                    self.signal_trace.append(state)
                if self.native_program:
                    self._track_native(state)
            for hook in self.second_hooks:
                hook(self)

    def _track_native(self, state: str) -> None:
        active = self.layout.phase_of_state(state)
        if active is None:
            self.signal_colour = "y"
            return
        if active != self.phase or self.signal_colour != "G":
            if active != self.phase:
                self.stats["switches"] += 1
            self.phase = active
            self.green_elapsed = 0
        self.signal_colour = "G"
        self.green_elapsed += 1

    def _switch(self, target: int) -> None:
        self._set_state(self.layout.yellow[self.phase], "y")
        self._advance(self.yellow)
        if self.all_red > 0:
            self._set_state(self.layout.all_red, "r")
            self._advance(self.all_red)
        self.phase = int(target)
        self._set_state(self.layout.green[self.phase], "G")
        self._advance(self.min_green)
        self.green_elapsed = self.min_green
        self.stats["switches"] += 1

    def _forced_target(self, snap: dict[str, Any]) -> int:
        """Longest current wait among the other approaches; ties go to the next in cycle order."""
        candidates = [(self.phase + k) % self.n_app for k in range(1, self.n_app)]
        return max(candidates, key=lambda a: snap["max_wait"][a])

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        prev = self.snap
        t0 = self.t
        forced = False
        if self.native_program:
            self._advance(self.delta)
            snap = self._snapshot()
        else:
            action = int(action)
            if action == self.phase:
                extend = min(self.delta, self.max_green - self.green_elapsed)
                self._advance(extend)
                self.green_elapsed += extend
            else:
                self._switch(action)
            snap = self._snapshot()
            if self.green_elapsed >= self.max_green and self.t < self.horizon:
                self._switch(self._forced_target(snap))
                self.stats["forced_switches"] += 1
                forced = True
                snap = self._snapshot()

        reward = float(self.reward_fn(prev, snap))
        self.snap = snap
        self.stats["decisions"] += 1
        self.stats["episode_reward"] += reward
        truncated = self.t >= self.horizon
        info = dict(snap)
        info["dt"] = self.t - t0
        info["forced"] = forced
        if truncated:
            info["episode_stats"] = self.episode_stats()
        return self._obs(), reward, False, truncated, info

    # ------------------------------------------------------------------ observation
    def _snapshot(self) -> dict[str, Any]:
        veh, lane = self.api.vehicle, self.api.lane
        pcu = self.pcu
        queue_in = np.zeros(self.n_lanes)
        density_in = np.zeros(self.n_lanes)
        halting = np.zeros(self.n_app)
        wait_by_class = np.zeros(len(CLASSES))
        max_wait = np.zeros(self.n_app)
        n_vehicles = 0
        for li, ln in enumerate(self.layout.in_lanes):
            a = self.layout.lane_approach[li]
            for vid in lane.getLastStepVehicleIDs(ln):
                c = CODE_INDEX[vid.split("-")[2]]
                n_vehicles += 1
                density_in[li] += pcu[c]
                if veh.getSpeed(vid) < HALT_SPEED:
                    queue_in[li] += pcu[c]
                    halting[a] += 1
                w = veh.getAccumulatedWaitingTime(vid)
                wait_by_class[c] += w
                if w > max_wait[a]:
                    max_wait[a] = w
        queue_out = np.zeros(len(self.layout.out_lanes))
        for li, ln in enumerate(self.layout.out_lanes):
            if lane.getLastStepHaltingNumber(ln) > 0:
                for vid in lane.getLastStepVehicleIDs(ln):
                    if veh.getSpeed(vid) < HALT_SPEED:
                        queue_out[li] += pcu[CODE_INDEX[vid.split("-")[2]]]
        return {
            "t": self.t,
            "phase": self.phase,
            "green_elapsed": self.green_elapsed,
            "queue_in": queue_in,
            "density_in": density_in,
            "queue_out": queue_out,
            "halting": halting,
            "wait_by_class": wait_by_class,
            "total_wait": float(wait_by_class.sum()),
            "max_wait": max_wait,
            "n_vehicles": n_vehicles,
            "movements": self.layout.movements,
        }

    def _obs(self) -> np.ndarray:
        return build_obs(self.snap, self.capacity, self.n_app, self.max_green, self.T, self.obs_mask)

    def episode_stats(self) -> dict[str, float]:
        s = self.stats
        seconds = max(self.t, 1)
        pending = len(self.api.simulation.getPendingVehicles()) if self.api is not None else 0
        return {
            "pending": float(pending),
            "seconds": float(self.t),
            "avg_queue": s["halting_seconds"] / seconds,
            "teleports": float(s["teleports"]),
            "collisions": float(s["collisions"]),
            "forced_switches": float(s["forced_switches"]),
            "switches": float(s["switches"]),
            "departed": float(s["departed"]),
            "arrived": float(s["arrived"]),
            "decisions": float(s["decisions"]),
            "episode_reward": float(s["episode_reward"]),
            "sumo_seed": float(self.sumo_seed),
        }
