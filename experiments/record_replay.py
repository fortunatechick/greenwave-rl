"""Record side-by-side replays for the website (spec Section 11.2).

Both sides of a scene run the same regime and the same SUMO seed, so they see the same
arrivals. One frame per simulated second; positions are metres x 10 as integers.

    python experiments/record_replay.py                    # the six scenes
    python experiments/record_replay.py --scenes hero surge
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.config import CLASSES, CODE_INDEX, class_vector, load_cfg  # noqa: E402
from greenwave.env.signal_env import HALT_SPEED, SignalEnv  # noqa: E402
from greenwave.jobs import best_job  # noqa: E402
from greenwave.runner import BASELINES, make_controller, run_episode  # noqa: E402
from greenwave.web_schema import Replay  # noqa: E402

VIEW_HALF_M = 150.0  # vehicles further than this from the junction centre are not recorded
OUT = ROOT / "web" / "public" / "data" / "replays"

LABELS = {
    "fixed_matched": "Fixed-time (Webster, tuned for this demand)",
    "fixed_peak": "Fixed-time (Webster, peak plan)",
    "actuated": "Actuated",
    "max_pressure": "Max-pressure",
    "random": "Random phase",
    "ddqn_fair__peak": "GreenWave (ours)",
    "ddqn_fair__skewed": "GreenWave (ours)",
    "ddqn_fair__surge": "GreenWave (ours)",
    "ddqn_fair__low": "GreenWave trained on low demand only",
    "ddqn_fair__dr": "GreenWave with domain randomisation",
    "abl_nofair__skewed": "Agent without the fairness penalty",
    "abl_ref__skewed": "GreenWave (ours, fairness penalty on)",
    "abl_vehicle_fair__peak": "Agent counting vehicles, not passengers",
    "abl_ref__peak": "GreenWave (ours, passenger-weighted)",
}

# left / right are baselines or training families; the best training seed of a family is used.
SCENES: dict[str, dict[str, Any]] = {
    "hero": {
        "regime": "peak", "left": "fixed_peak", "right": "ddqn_fair__peak", "t0": 600, "t1": 1200,
        "title": "Fixed-time against a learned policy",
        "caption": "Same traffic, same seed. Watch how long each queue stands before it is served.",
    },
    "surge": {
        "regime": "surge", "left": "fixed_matched", "right": "ddqn_fair__dr", "t0": 1400, "t1": 2200,
        "title": "A ten-minute surge on the east approach",
        "caption": "At 1500 s the east approach jumps to 2.5 times peak. The timer keeps its plan; "
                   "the agent moves green to where the queue is.",
        "events": [{"t": 1500, "label": "Surge starts on E"}, {"t": 2100, "label": "Surge ends"}],
    },
    "starvation": {
        "regime": "skewed", "left": "abl_nofair__skewed", "right": "abl_ref__skewed",
        "t0": 600, "t1": 1400,
        "title": "What the fairness penalty is for",
        "caption": "One approach carries most of the traffic. Watch the longest wait on the minor "
                   "roads with and without the penalty.",
    },
    "bus": {
        "regime": "peak", "left": "abl_vehicle_fair__peak", "right": "abl_ref__peak",
        "t0": 600, "t1": 1200,
        "title": "Counting passengers, not vehicles",
        "caption": "Turn on bus highlighting. With passenger weighting, an approach holding a bus "
                   "is worth more green.",
    },
    "honest": {
        "regime": "peak", "left": "max_pressure", "right": "ddqn_fair__peak", "t0": 600, "t1": 1200,
        "title": "The honest comparison: max-pressure",
        "caption": "A training-free rule against deep RL on one junction. See the Results page "
                   "for who wins on which metric.",
    },
    "generalisation": {
        "regime": "surge", "left": "ddqn_fair__low", "right": "ddqn_fair__dr",
        "t0": 1400, "t1": 2200,
        "title": "Trained on the wrong traffic",
        "caption": "Left: a policy that only ever saw low demand. Right: trained with randomised "
                   "demand. Both meet a surge neither was trained on.",
        "events": [{"t": 1500, "label": "Surge starts on E"}, {"t": 2100, "label": "Surge ends"}],
    },
}  # fmt: skip


class Recorder:
    """Per-second hook: vehicle frames, signal state and the HUD / chart series."""

    def __init__(self, t0: int, t1: int) -> None:
        self.t0, self.t1 = t0, t1
        self.index: dict[str, int] = {}
        self.veh_class: list[int] = []
        self.frames: list[list[int]] = []
        self.signal: list[str] = []
        self.phase: list[int] = []
        self.wait_now: list[float] = []
        self.queue: list[list[int]] = []
        self.person_cum: list[float] = []
        self.max_wait: list[float] = []
        self.weights = np.asarray(class_vector(load_cfg()["demand"]["passenger_weights"]))
        self._person_seconds = 0.0

    def __call__(self, env: SignalEnv) -> None:
        if not (self.t0 < env.t <= self.t1):
            return
        veh, lane = env.api.vehicle, env.api.lane
        frame: list[int] = []
        cx, cy = env.layout.center
        for vid in veh.getIDList():
            x, y = veh.getPosition(vid)
            x, y = x - cx, y - cy
            if abs(x) > VIEW_HALF_M or abs(y) > VIEW_HALF_M:
                continue
            idx = self.index.get(vid)
            if idx is None:
                idx = self.index[vid] = len(self.veh_class)
                self.veh_class.append(CODE_INDEX[vid.split("-")[2]])
            frame += [idx, int(round(x * 10)), int(round(y * 10)), int(round(veh.getAngle(vid))) % 360]
        self.frames.append(frame)
        self.signal.append(env.api.trafficlight.getRedYellowGreenState(env.tls))
        self.phase.append(int(env.phase))

        queue = [0] * env.n_app
        waits: list[float] = []
        for li, ln in enumerate(env.layout.in_lanes):
            a = env.layout.lane_approach[li]
            for vid in lane.getLastStepVehicleIDs(ln):
                waits.append(veh.getAccumulatedWaitingTime(vid))
                if veh.getSpeed(vid) < HALT_SPEED:
                    queue[a] += 1
                    self._person_seconds += self.weights[CODE_INDEX[vid.split("-")[2]]]
        self.queue.append(queue)
        self.wait_now.append(round(float(np.mean(waits)) if waits else 0.0, 1))
        self.max_wait.append(round(float(max(waits)) if waits else 0.0, 1))
        self.person_cum.append(round(self._person_seconds / 60.0, 1))  # person-minutes

    def side(self) -> dict[str, Any]:
        return {
            "veh_class": self.veh_class,
            "frames": self.frames,
            "signal": self.signal,
            "phase": self.phase,
            "series": {
                "wait_now": self.wait_now,
                "queue_by_approach": self.queue,
                "person_wait_cum": self.person_cum,
                "max_wait": self.max_wait,
            },
        }


def resolve(key: str) -> str:
    return key if key in BASELINES else best_job(key)


def record_side(controller_key: str, regime: str, seed: int, t0: int, t1: int) -> dict[str, Any]:
    import torch

    torch.set_num_threads(1)
    recorder = Recorder(t0, t1)
    run_episode(
        make_controller(controller_key, regime), regime, seed,
        episode_seconds=t1, with_tripinfo=False, hooks=[recorder],
    )  # fmt: skip
    return recorder.side()


def record_scene(
    name: str, scene: dict[str, Any], seed: int, out_dir: Path = OUT, mock: bool = False,
    labels: dict[str, str] | None = None,
) -> Path:  # fmt: skip
    labels = {**LABELS, **(labels or {})}
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = {
            side: pool.submit(record_side, resolve(scene[side]), scene["regime"], seed,
                              scene["t0"], scene["t1"])
            for side in ("left", "right")
        }  # fmt: skip
        sides = {side: fut.result() for side, fut in futures.items()}
    replay = {
        "scene": name,
        "title": scene["title"],
        "caption": scene["caption"],
        "left": {"controller": scene["left"], "label": labels.get(scene["left"], scene["left"])},
        "right": {"controller": scene["right"], "label": labels.get(scene["right"], scene["right"])},
        "regime": scene["regime"],
        "seed": seed,
        "t0": scene["t0"],
        "t1": scene["t1"],
        "dt": 1,
        "classes": list(CLASSES),
        "events": scene.get("events", []),
        "sides": sides,
        "mock": mock,
    }
    Replay.model_validate(replay)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    path.write_text(json.dumps(replay, separators=(",", ":")), encoding="utf-8")
    n_veh = max(len(sides["left"]["veh_class"]), len(sides["right"]["veh_class"]))
    print(f"{name:15s} {path.stat().st_size / 1e6:5.2f} MB  {scene['t1'] - scene['t0']} frames, "
          f"up to {n_veh} vehicles per side")  # fmt: skip
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes", nargs="*", default=list(SCENES))
    args = parser.parse_args()
    seed = int(load_cfg()["sim"]["seeds"]["replay"])
    for name in args.scenes:
        record_scene(name, SCENES[name], seed)
    total = sum(p.stat().st_size for p in OUT.glob("*.json"))
    print(f"replays total {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
