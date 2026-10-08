"""docs/demo.gif: a short side-by-side clip of the hero replay for the README.

    python experiments/make_readme_gif.py [--scene hero]

Drawn with Pillow from the same replay and network files the website uses.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "public" / "data"
PANEL, GAP, HEADER = 340, 12, 30
HALF_M = 75.0  # metres from the junction centre shown in each panel
BG, ROAD, ROAD_LINE, TEXT, MUTED = (10, 12, 15), (27, 32, 39), (52, 59, 70), (232, 234, 237), (138, 147, 160)
VEH = [(125, 211, 252), (253, 224, 71), (203, 213, 225), (196, 181, 253)]
DIMS = [(1.9, 0.8), (2.6, 1.4), (4.3, 1.8), (12.0, 2.5)]
SIGNAL = {"G": (61, 220, 132), "g": (61, 220, 132), "y": (255, 176, 32), "r": (255, 77, 79)}
SCALE = PANEL / (2 * HALF_M)


def px(x: float, y: float, ox: int) -> tuple[float, float]:
    return ox + PANEL / 2 + x * SCALE, HEADER + PANEL / 2 - y * SCALE


def road_layer(network: dict) -> Image.Image:
    img = Image.new("RGB", (PANEL, PANEL + HEADER), BG)
    d = ImageDraw.Draw(img)
    for colour, shrink in ((ROAD_LINE, -0.25), (ROAD, 0.2)):
        for lane in network["lanes"]:
            pts = [px(x, y, 0) for x, y in lane["shape"]]
            d.line(pts, fill=colour, width=max(1, round((lane["width"] - shrink) * SCALE)))
    d.polygon([px(x, y, 0) for x, y in network["junction_shape"]], fill=ROAD)
    return img


def draw_vehicle(d: ImageDraw.ImageDraw, cls: int, x: float, y: float, angle: float, ox: int) -> None:
    length, width = DIMS[cls]
    a = math.radians(angle)
    fx, fy = math.sin(a), math.cos(a)  # heading in world coordinates (0 deg = north)
    lx, ly = -fy, fx
    w = max(width, 1.0) / 2
    corners = [(x + lx * w, y + ly * w), (x - lx * w, y - ly * w),
               (x - lx * w - fx * length, y - ly * w - fy * length),
               (x + lx * w - fx * length, y + ly * w - fy * length)]  # fmt: skip
    d.polygon([px(cx, cy, ox) for cx, cy in corners], fill=VEH[cls])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="hero")
    parser.add_argument("--frames", type=int, default=90)
    parser.add_argument("--step", type=int, default=3, help="simulated seconds per frame")
    args = parser.parse_args()
    replay_path = DATA / "replays" / f"{args.scene}.json"
    if not replay_path.exists():
        sys.exit(f"{replay_path} missing: record replays first")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    network = json.loads((DATA / "network.json").read_text(encoding="utf-8"))
    base = road_layer(network)
    font = ImageFont.load_default()
    n = min(args.frames, (replay["t1"] - replay["t0"]) // args.step)
    frames = []
    for k in range(n):
        f = k * args.step
        canvas = Image.new("RGB", (PANEL * 2 + GAP, PANEL + HEADER), BG)
        d = ImageDraw.Draw(canvas)
        for i, side in enumerate(("left", "right")):
            ox = i * (PANEL + GAP)
            canvas.paste(base, (ox, 0))
            data = replay["sides"][side]
            frame = data["frames"][f]
            for j in range(0, len(frame), 4):
                draw_vehicle(d, data["veh_class"][frame[j]], frame[j + 1] / 10, frame[j + 2] / 10, frame[j + 3], ox)
            for sig in network["signals"]:
                sx, sy = px(sig["pos"][0] * 1.9, sig["pos"][1] * 1.9, ox)
                d.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=SIGNAL.get(data["signal"][f][sig["link"]], MUTED))
            d.rectangle([ox, 0, ox + PANEL, HEADER - 2], fill=BG)
            d.text((ox + 6, 4), replay[side]["label"][:46], fill=TEXT if i else MUTED, font=font)
            d.text((ox + 6, 16), f"mean wait {data['series']['wait_now'][f]:5.1f} s   longest "
                                 f"{data['series']['max_wait'][f]:4.0f} s", fill=MUTED, font=font)  # fmt: skip
        frames.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE, colors=48))
    out = ROOT / "docs" / "demo.gif"
    out.parent.mkdir(exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True)
    tag = " (MOCK preview replay)" if replay.get("mock") else ""
    print(f"{out.relative_to(ROOT)}: {len(frames)} frames, {out.stat().st_size / 1e6:.2f} MB{tag}")


if __name__ == "__main__":
    main()
