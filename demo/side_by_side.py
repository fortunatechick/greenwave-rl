"""Live side-by-side demo: two sumo-gui windows, same routes, same seed.

    python demo/side_by_side.py                              # hero scene
    python demo/side_by_side.py --scene starvation
    python demo/side_by_side.py --left fixed_matched --right ddqn_fair__dr --regime surge
    python demo/side_by_side.py --surge-at 300               # scripted surge instead of a key press

Press Enter in this terminal at any time to inject a surge (30 vehicles over 60 s) on one
approach of BOTH simulations. Metrics stream to results/raw/demo_live.jsonl; watch them
with:  streamlit run demo/dashboard.py
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.record_replay import LABELS, SCENES, resolve  # noqa: E402
from greenwave.config import load_cfg  # noqa: E402
from greenwave.env.signal_env import SignalEnv  # noqa: E402
from greenwave.runner import make_controller  # noqa: E402
from greenwave.tls import THROUGH_OF  # noqa: E402

LIVE = ROOT / "results" / "raw" / "demo_live.jsonl"
SURGE_VEHICLES, SURGE_SECONDS = 30, 60


class Surge:
    """Adds the same extra vehicles to both simulations once `start` is set."""

    def __init__(self, approach: str) -> None:
        self.approach = approach
        self.start: int | None = None
        self.count = 0
        self.added: dict[str, int] = {}

    def trigger(self, t: int) -> None:
        if self.start is None or t > self.start + SURGE_SECONDS:
            self.start = t
            self.count += 1
            self.added = {}
            print(f"\n>>> surge #{self.count} on {self.approach} starting at t = {t} s", flush=True)

    def hook(self, env: SignalEnv) -> None:
        if self.start is None:
            return
        k = (env.t - self.start) // (SURGE_SECONDS // SURGE_VEHICLES)
        done = self.added.get(env.handle.label, 0)
        if not (0 <= k < SURGE_VEHICLES) or k < done:
            return
        api = env.api
        route = f"surge_{self.approach}"
        if route not in api.route.getIDList():
            api.route.add(route, [f"{self.approach}_in", f"{THROUGH_OF[self.approach]}_out"])
        # Ids follow the demand convention <origin>-<dest>-<class code>-<window>.<n>.
        vid = f"{self.approach}-{THROUGH_OF[self.approach]}-car-s{self.count}.{k}"
        api.vehicle.add(vid, route, typeID="car", departLane="best", departSpeed="max")
        self.added[env.handle.label] = done + 1


def make_side(label: str, key: str, regime: str, x: int, seconds: int, delay: int) -> tuple[SignalEnv, Any]:
    controller = make_controller(resolve(key), regime)
    kwargs: dict[str, Any] = {"reward": "fair"}
    kwargs.update(getattr(controller, "env_kwargs", None) or {})
    kwargs.update(regime=regime, episode_seconds=seconds, gui=True, label=label, libsumo=False,
                  native_program=controller.native_program,
                  extra_sumo_args=["--start", "true", "--quit-on-end", "true", "--delay", str(delay),
                                   "--window-size", "760,720", "--window-pos", f"{x},40"])  # fmt: skip
    return SignalEnv(**kwargs), controller


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scene", default="hero", choices=list(SCENES))
    parser.add_argument("--left")
    parser.add_argument("--right")
    parser.add_argument("--regime")
    parser.add_argument("--seed", type=int, default=load_cfg()["sim"]["seeds"]["replay"])
    parser.add_argument("--seconds", type=int, default=1800)
    parser.add_argument("--delay", type=int, default=60, help="sumo-gui delay per step in ms")
    parser.add_argument("--surge-approach", default="E")
    parser.add_argument("--surge-at", type=int, default=None, help="inject a surge at this simulation second")
    args = parser.parse_args()

    scene = SCENES[args.scene]
    left, right = args.left or scene["left"], args.right or scene["right"]
    regime = args.regime or scene["regime"]
    print(f"left : {LABELS.get(left, left)}\nright: {LABELS.get(right, right)}\nregime {regime}, seed {args.seed}")

    surge = Surge(args.surge_approach)
    sides: dict[str, dict[str, Any]] = {}
    for label, key, x in (("left", left, 20), ("right", right, 800)):
        env, controller = make_side(label, key, regime, x, args.seconds, args.delay)
        env.second_hooks.append(surge.hook)
        controller.reset()
        obs, info = env.reset(seed=args.seed, options={"sumo_seed": args.seed})
        sides[label] = {"env": env, "controller": controller, "obs": obs, "info": info, "done": False,
                        "name": LABELS.get(key, key)}  # fmt: skip

    def wait_for_enter() -> None:
        while True:
            try:
                input()
            except EOFError:
                return
            surge.trigger(max(s["env"].t for s in sides.values()))

    threading.Thread(target=wait_for_enter, daemon=True).start()
    print("Press Enter to inject a surge. Close the SUMO windows or press Ctrl+C to stop.")

    LIVE.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        with open(LIVE, "w", encoding="utf-8") as out:
            while not all(s["done"] for s in sides.values()):
                # Advance whichever simulation is behind, so both stay within one decision.
                side = min((s for s in sides.values() if not s["done"]), key=lambda s: s["env"].t)
                env = side["env"]
                if args.surge_at is not None and surge.start is None and env.t >= args.surge_at:
                    surge.trigger(env.t)
                action = side["controller"].act(side["obs"], side["info"])
                side["obs"], _, _, side["done"], side["info"] = env.step(action)
                info = side["info"]
                out.write(json.dumps({
                    "side": env.handle.label, "name": side["name"], "t": int(env.t),
                    "queue": float(np.sum(info["halting"])), "queue_by_approach": info["halting"].tolist(),
                    "total_wait": float(info["total_wait"]), "max_wait": float(np.max(info["max_wait"])),
                    "mean_wait": float(info["total_wait"] / max(info["n_vehicles"], 1)), "phase": int(info["phase"]),
                    "wall": round(time.time() - started, 1),
                }) + "\n")  # fmt: skip
                out.flush()
    except KeyboardInterrupt:
        print("stopped")
    except Exception as err:  # noqa: BLE001 - closing a SUMO window ends the demo cleanly
        print(f"demo ended: {type(err).__name__}")
    finally:
        for s in sides.values():
            s["env"].close()


if __name__ == "__main__":
    main()
