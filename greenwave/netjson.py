"""Network geometry for the website's replay renderer (network.json)."""

from __future__ import annotations

import math
from typing import Any

from greenwave.config import load_cfg, net_path
from greenwave.env.signal_env import get_layout

VIEW_HALF_M = 150.0


def network_json() -> dict[str, Any]:
    import sumolib

    cfg = load_cfg()
    j = cfg["junction"]
    net = sumolib.net.readNet(str(net_path("junction")))
    layout = get_layout("junction")
    cx, cy = layout.center
    lanes: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []
    for ai, a in enumerate(j["approaches"]):
        ends: list[tuple[float, float]] = []
        heading = 0.0
        for direction in ("in", "out"):
            for lane in net.getEdge(f"{a}_{direction}").getLanes():
                shape = [(round(x - cx, 2), round(y - cy, 2)) for x, y in lane.getShape()]
                lanes.append(
                    {"id": lane.getID(), "approach": a, "dir": direction,
                     "width": float(lane.getWidth()), "shape": shape}
                )  # fmt: skip
                if direction == "in":
                    ends.append(shape[-1])
                    (x0, y0), (x1, y1) = shape[-2], shape[-1]
                    heading = math.degrees(math.atan2(x1 - x0, y1 - y0)) % 360  # 0 = north, clockwise
        signals.append(
            {
                "approach": a,
                "pos": (round(sum(p[0] for p in ends) / len(ends), 2),
                        round(sum(p[1] for p in ends) / len(ends), 2)),
                "angle": round(heading, 1),
                "link": layout.through_link[ai],
            }
        )  # fmt: skip
    return {
        "bounds": (-VIEW_HALF_M, -VIEW_HALF_M, VIEW_HALF_M, VIEW_HALF_M),
        "lanes": lanes,
        "junction_shape": [
            (round(x - cx, 2), round(y - cy, 2)) for x, y in net.getNode(j["tls_id"]).getShape()
        ],
        "signals": signals,
        "approaches": list(j["approaches"]),
        "facts": {
            "name": j["name"],
            "lanes_in": j["lanes_in"],
            "lanes_out": j["lanes_out"],
            "approach_length_m": j["approach_length_m"],
            "lane_width_m": j["lane_width_m"],
            "free_left": j["free_left"],
            "phases": layout.n_phases,
            "left_hand_traffic": True,
            "min_green": cfg["sim"]["min_green"],
            "max_green": cfg["sim"]["max_green"],
            "yellow": cfg["sim"]["yellow"],
            "decision_interval": cfg["sim"]["decision_interval"],
        },
    }
