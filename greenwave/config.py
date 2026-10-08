"""Config loading. Every script reads constants from configs/*.yaml through here."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs"

CLASSES: tuple[str, ...] = ("two_wheeler", "auto_rickshaw", "car", "bus")
CLASS_CODES: dict[str, str] = {
    "two_wheeler": "tw",
    "auto_rickshaw": "au",
    "car": "car",
    "bus": "bus",
}
CODE_INDEX: dict[str, int] = {CLASS_CODES[c]: i for i, c in enumerate(CLASSES)}
REGIMES: tuple[str, ...] = ("low", "peak", "skewed", "surge")


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8-sig") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def load_cfg() -> dict[str, Any]:
    """Return all base configs merged under one dict keyed by file stem."""
    names = ("junction", "sim", "demand", "rewards", "train")
    return {n: load_yaml(CONFIG_DIR / f"{n}.yaml") for n in names if (CONFIG_DIR / f"{n}.yaml").exists()}


def class_vector(mapping: dict[str, float]) -> list[float]:
    """Order a per-class mapping by CLASSES."""
    return [float(mapping[c]) for c in CLASSES]


def net_path(network: str = "junction") -> Path:
    if network == "toy":
        return ROOT / "network" / "toy" / "toy.net.xml"
    return ROOT / "network" / "junction.net.xml"


def route_path(regime: str, network: str = "junction") -> Path:
    if network == "toy":
        return ROOT / "network" / "toy" / "toy.rou.xml"
    return ROOT / "demand" / "routes" / f"{regime}.rou.xml"


def vtypes_path() -> Path:
    return ROOT / "demand" / "vtypes.add.xml"


def dr_pool_files() -> list[str]:
    return sorted(str(p) for p in (ROOT / "demand" / "dr_pool").glob("dr_*.rou.xml"))
