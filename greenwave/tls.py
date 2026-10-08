"""Signal layout: which link belongs to which approach, and the state strings of the
approach-wise split phasing (one green phase per approach, left-hand traffic)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# Left-hand traffic: a driver entering from N heads south, so their left is east.
LEFT_OF = {"N": "E", "E": "S", "S": "W", "W": "N"}
THROUGH_OF = {"N": "S", "E": "W", "S": "N", "W": "E"}
RIGHT_OF = {"N": "W", "E": "N", "S": "E", "W": "S"}


def turn_of(origin: str, dest: str) -> str:
    if LEFT_OF[origin] == dest:
        return "left"
    if THROUGH_OF[origin] == dest:
        return "through"
    if RIGHT_OF[origin] == dest:
        return "right"
    raise ValueError(f"no movement {origin}->{dest}")


def dest_of(origin: str, turn: str) -> str:
    return {"left": LEFT_OF, "through": THROUGH_OF, "right": RIGHT_OF}[turn][origin]


@dataclass
class TlsLayout:
    tls_id: str
    approaches: list[str]
    in_lanes: list[str]
    out_lanes: list[str]
    lane_approach: list[int]  # approach index of each incoming lane
    out_lane_approach: list[int]
    lane_length: list[float]  # incoming lanes, metres
    links: list[tuple[int, int, int, str]]  # (in lane idx, out lane idx, approach idx, turn)
    green: list[str] = field(default_factory=list)
    yellow: list[str] = field(default_factory=list)
    all_red: str = ""
    movements: list[list[tuple[int, int]]] = field(default_factory=list)
    through_link: list[int] = field(default_factory=list)

    @property
    def n_phases(self) -> int:
        return len(self.approaches)

    def phase_of_state(self, state: str) -> int | None:
        """Approach currently holding a protected green, or None during yellow / all-red."""
        for a, link in enumerate(self.through_link):
            if state[link] == "G":
                return a
        return None


def read_layout(
    net_file: str | Path, approaches: Sequence[str], free_left: bool, tls_id: str = "J0"
) -> TlsLayout:
    import sumolib

    net = sumolib.net.readNet(str(net_file))
    conns = sorted(net.getTLS(tls_id).getConnections(), key=lambda c: c[2])
    order = {a: i for i, a in enumerate(approaches)}

    def lanes_of(suffix: str) -> list:
        lanes = []
        for a in approaches:
            lanes.extend(net.getEdge(f"{a}_{suffix}").getLanes())
        return lanes

    in_lanes, out_lanes = lanes_of("in"), lanes_of("out")
    in_idx = {ln.getID(): i for i, ln in enumerate(in_lanes)}
    out_idx = {ln.getID(): i for i, ln in enumerate(out_lanes)}

    links: list[tuple[int, int, int, str]] = []
    for expected, (lane_in, lane_out, link_no) in enumerate(conns):
        if link_no != expected:
            raise ValueError(f"non-contiguous link indices at {tls_id}: {link_no}")
        origin = lane_in.getEdge().getID().split("_")[0]
        dest = lane_out.getEdge().getID().split("_")[0]
        links.append(
            (in_idx[lane_in.getID()], out_idx[lane_out.getID()], order[origin], turn_of(origin, dest))
        )

    layout = TlsLayout(
        tls_id=tls_id,
        approaches=list(approaches),
        in_lanes=[ln.getID() for ln in in_lanes],
        out_lanes=[ln.getID() for ln in out_lanes],
        lane_approach=[order[ln.getEdge().getID().split("_")[0]] for ln in in_lanes],
        out_lane_approach=[order[ln.getEdge().getID().split("_")[0]] for ln in out_lanes],
        lane_length=[float(ln.getLength()) for ln in in_lanes],
        links=links,
    )

    def state(active: int | None, colour: str) -> str:
        chars = []
        for _, _, a, turn in links:
            free = free_left and turn == "left"
            if a == active:
                chars.append("g" if (free and colour == "y") else colour)
            else:
                chars.append("g" if free else "r")
        return "".join(chars)

    n = len(approaches)
    layout.green = [state(p, "G") for p in range(n)]
    layout.yellow = [state(p, "y") for p in range(n)]
    layout.all_red = state(None, "r")
    layout.movements = [[(i, o) for i, o, a, _ in links if a == p] for p in range(n)]
    layout.through_link = [
        next(k for k, (_, _, a, turn) in enumerate(links) if a == p and turn == "through")
        for p in range(n)
    ]
    return layout


def program_xml(
    layout: TlsLayout,
    greens: Sequence[float],
    yellow: float,
    all_red: float = 0.0,
    program_id: str = "0",
    actuated: bool = False,
    min_dur: float = 10.0,
    max_dur: float = 60.0,
    max_gap: float = 3.0,
) -> str:
    """A <tlLogic> element: green(p), yellow(p) [, all-red] for each approach in cycle order."""
    kind = "actuated" if actuated else "static"
    lines = [f'<tlLogic id="{layout.tls_id}" type="{kind}" programID="{program_id}" offset="0">']
    if actuated:
        lines.append(f'    <param key="max-gap" value="{max_gap}"/>')
        lines.append('    <param key="show-detectors" value="false"/>')
    for p in range(layout.n_phases):
        if actuated:
            lines.append(
                f'    <phase duration="{min_dur:g}" minDur="{min_dur:g}" maxDur="{max_dur:g}" '
                f'state="{layout.green[p]}"/>'
            )
        else:
            lines.append(f'    <phase duration="{greens[p]:g}" state="{layout.green[p]}"/>')
        lines.append(f'    <phase duration="{yellow:g}" state="{layout.yellow[p]}"/>')
        if all_red > 0:
            lines.append(f'    <phase duration="{all_red:g}" state="{layout.all_red}"/>')
    lines.append("</tlLogic>")
    return "\n".join(lines)


def write_program_file(path: str | Path, xml: str) -> None:
    Path(path).write_text(f"<additional>\n{xml}\n</additional>\n", encoding="utf-8")


def patch_net_program(net_file: str | Path, xml: str, tls_id: str = "J0") -> None:
    """Replace the netconvert-generated program of `tls_id` inside a .net.xml."""
    text = Path(net_file).read_text(encoding="utf-8")
    pattern = re.compile(rf'<tlLogic id="{tls_id}".*?</tlLogic>', re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"no tlLogic for {tls_id} in {net_file}")
    indented = "\n".join("    " + ln if i else ln for i, ln in enumerate(xml.splitlines()))
    Path(net_file).write_text(pattern.sub(lambda _: indented, text, count=1), encoding="utf-8")
