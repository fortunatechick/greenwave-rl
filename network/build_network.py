"""Build the junction network.

Path B (default): plain XML generated from configs/junction.yaml, then netconvert --lefthand.
Path A (OSM) is attempted only when `bbox` is set; it falls back to Path B.

    python network/build_network.py            # network/junction.net.xml
    python network/build_network.py --toy      # network/toy/toy.net.xml
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.config import load_cfg  # noqa: E402
from greenwave.sumo_utils import sumo_binary  # noqa: E402
from greenwave.tls import (  # noqa: E402
    LEFT_OF,
    RIGHT_OF,
    THROUGH_OF,
    patch_net_program,
    program_xml,
    read_layout,
    write_program_file,
)

UNIT = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}

TOY_JUNCTION: dict[str, Any] = {
    "name": "Toy symmetric 4-way",
    "approaches": ["N", "E", "S", "W"],
    "lanes_in": {"N": 1, "E": 1, "S": 1, "W": 1},
    "lanes_out": {"N": 1, "E": 1, "S": 1, "W": 1},
    "approach_length_m": 150,
    "lane_width_m": 3.5,
    "speed_limit_mps": 13.89,
    "free_left": False,
    "tls_id": "J0",
}


def write_plain(j: dict[str, Any], out_dir: Path, stem: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    length, width, speed = j["approach_length_m"], j["lane_width_m"], j["speed_limit_mps"]
    tls = j["tls_id"]

    nodes = [f'    <node id="{tls}" x="0" y="0" type="traffic_light" tl="{tls}"/>']
    edges, conns = [], []
    for a in j["approaches"]:
        ux, uy = UNIT[a]
        nodes.append(f'    <node id="n{a}" x="{ux * length}" y="{uy * length}" type="priority"/>')
        edges.append(
            f'    <edge id="{a}_in" from="n{a}" to="{tls}" numLanes="{j["lanes_in"][a]}" '
            f'speed="{speed}" width="{width}" priority="2"/>'
        )
        edges.append(
            f'    <edge id="{a}_out" from="{tls}" to="n{a}" numLanes="{j["lanes_out"][a]}" '
            f'speed="{speed}" width="{width}" priority="2"/>'
        )

    # Lane 0 is the kerb-side (left) lane in left-hand traffic: left turns leave from it,
    # right turns from the innermost lane, through traffic from every lane.
    for a in j["approaches"]:
        n_in = j["lanes_in"][a]

        def conn(dest: str, lane_from: int, lane_to: int, origin: str = a) -> str:
            return (
                f'    <connection from="{origin}_in" to="{dest}_out" '
                f'fromLane="{lane_from}" toLane="{lane_to}"/>'
            )

        conns.append(conn(LEFT_OF[a], 0, 0))
        m_through = j["lanes_out"][THROUGH_OF[a]]
        for lane in range(n_in):
            conns.append(conn(THROUGH_OF[a], lane, min(lane, m_through - 1)))
        conns.append(conn(RIGHT_OF[a], n_in - 1, j["lanes_out"][RIGHT_OF[a]] - 1))

    paths = {
        "nod": out_dir / f"{stem}.nod.xml",
        "edg": out_dir / f"{stem}.edg.xml",
        "con": out_dir / f"{stem}.con.xml",
    }
    paths["nod"].write_text("<nodes>\n" + "\n".join(nodes) + "\n</nodes>\n", encoding="utf-8")
    paths["edg"].write_text("<edges>\n" + "\n".join(edges) + "\n</edges>\n", encoding="utf-8")
    paths["con"].write_text(
        "<connections>\n" + "\n".join(conns) + "\n</connections>\n", encoding="utf-8"
    )
    return paths


def build_plain(j: dict[str, Any], plain_dir: Path, stem: str, net_out: Path, sim: dict) -> None:
    paths = write_plain(j, plain_dir, stem)
    cmd = [
        sumo_binary("netconvert"),
        "--lefthand", "true",
        "--node-files", str(paths["nod"]),
        "--edge-files", str(paths["edg"]),
        "--connection-files", str(paths["con"]),
        "--no-turnarounds", "true",
        "--junctions.corner-detail", "5",
        "--no-warnings", "true",
        "--output-file", str(net_out),
    ]  # fmt: skip
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    layout = read_layout(net_out, j["approaches"], j["free_left"], j["tls_id"])
    # Placeholder split (equal greens); Webster plans are loaded as additional programs.
    default = program_xml(
        layout, [25] * layout.n_phases, sim["yellow"], sim["all_red"], program_id="0"
    )
    patch_net_program(net_out, default, j["tls_id"])

    actuated = program_xml(
        layout,
        [],
        sim["yellow"],
        sim["all_red"],
        program_id="actuated",
        actuated=True,
        min_dur=sim["min_green"],
        max_dur=sim["max_green"],
    )
    write_program_file(net_out.parent / f"tls_actuated{'_toy' if stem == 'toy' else ''}.add.xml", actuated)

    check = read_layout(net_out, j["approaches"], j["free_left"], j["tls_id"])
    assert check.green == layout.green, "link order changed after patching"
    print(
        f"built {net_out.relative_to(ROOT)}: {len(layout.in_lanes)} incoming lanes, "
        f"{len(layout.links)} signal links, {layout.n_phases} green phases"
    )
    for p, a in enumerate(layout.approaches):
        print(f"  phase {p} ({a}): {layout.green[p]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toy", action="store_true")
    args = parser.parse_args()
    cfg = load_cfg()
    if args.toy:
        build_plain(
            TOY_JUNCTION, ROOT / "network" / "toy", "toy", ROOT / "network" / "toy" / "toy.net.xml",
            cfg["sim"],
        )  # fmt: skip
        return
    j = cfg["junction"]
    if j.get("bbox"):
        print("bbox set, but the OSM path is not used in this build; see DECISIONS.md. Using Path B.")
    build_plain(j, ROOT / "network" / "plain", "junction", ROOT / "network" / "junction.net.xml", cfg["sim"])


if __name__ == "__main__":
    main()
