"""The data contract: every file the website reads validates against greenwave/web_schema.py,
and the zod schemas on the web side name the same fields."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from greenwave.netjson import network_json
from greenwave.web_schema import (
    AblationRow,
    Corridor,
    Curve,
    FairnessEntry,
    Generalisation,
    MainRow,
    Meta,
    Network,
    PerClassRow,
    Replay,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIRS = [d for d in (ROOT / "web" / "public" / "data", ROOT / "web" / "fixtures") if (d / "meta.json").exists()]


def load(path: Path):  # noqa: ANN201
    return json.loads(path.read_text(encoding="utf-8"))


def test_network_json_matches_contract() -> None:
    net = Network.model_validate(network_json())
    assert {lane.approach for lane in net.lanes} == {"N", "E", "S", "W"}
    assert len(net.signals) == 4
    # Centred on the junction: the incoming lanes end near the origin.
    assert all(abs(s.pos[0]) < 20 and abs(s.pos[1]) < 20 for s in net.signals)


@pytest.mark.parametrize("data", DATA_DIRS, ids=lambda d: d.name)
def test_exported_files_validate(data: Path) -> None:
    meta = Meta.model_validate(load(data / "meta.json"))
    Network.model_validate(load(data / "network.json"))
    for row in load(data / "results" / "main.json"):
        MainRow.model_validate(row)
    for curve in load(data / "results" / "curves.json").values():
        c = Curve.model_validate(curve)
        assert len(c.steps) == len(c.mean) == len(c.std)
    for grid in load(data / "results" / "generalisation.json"):
        g = Generalisation.model_validate(grid)
        assert len(g.matrix) == len(g.regimes) and all(len(r) == len(g.regimes) for r in g.matrix)
    for entry in load(data / "results" / "fairness.json").values():
        e = FairnessEntry.model_validate(entry)
        assert e.ecdf_x == sorted(e.ecdf_x) and e.ecdf_y[-1] == pytest.approx(1.0)
    for row in load(data / "results" / "per_class.json"):
        PerClassRow.model_validate(row)
    for row in load(data / "results" / "ablations.json"):
        AblationRow.model_validate(row)
    corridor = Corridor.model_validate(load(data / "corridor.json"))
    for scene in corridor.scenes.values():
        for road in scene.roads.values():
            assert road.left_trip_s == pytest.approx(corridor.free_flow_s + corridor.signals * road.left_delay_s)
    if data.name == "fixtures":
        assert meta.mock, "fixtures must be flagged as mock data"


@pytest.mark.parametrize("data", DATA_DIRS, ids=lambda d: d.name)
def test_replays_validate(data: Path) -> None:
    replays = sorted((data / "replays").glob("*.json"))
    assert replays, "no replays exported"
    for path in replays:
        r = Replay.model_validate(load(path))
        n = r.t1 - r.t0
        for side in r.sides.values():
            assert len(side.frames) == len(side.signal) == len(side.phase) == n
            assert len(side.series.wait_now) == len(side.series.queue_by_approach) == n
            assert all(len(f) % 4 == 0 for f in side.frames)
            assert all(f[i] < len(side.veh_class) for f in side.frames[:: max(1, n // 20)] for i in range(0, len(f), 4))
        if data.name == "fixtures":
            assert r.mock


def test_real_export_is_not_mock_and_small_enough() -> None:
    data = ROOT / "web" / "public" / "data"
    if not (data / "meta.json").exists() or load(data / "meta.json")["mock"]:
        pytest.skip("public/data holds preview fixtures, not a real export")
    assert not any(load(p).get("mock") for p in (data / "replays").glob("*.json"))
    size = sum(p.stat().st_size for p in data.rglob("*") if p.is_file())
    assert size < 30e6, f"web/public/data is {size / 1e6:.1f} MB, over the 30 MB budget"


def test_zod_schema_names_the_same_fields() -> None:
    """Both sides of the contract must agree on field names (snake_case, shared)."""
    zod = (ROOT / "web" / "src" / "lib" / "schemas.mjs").read_text(encoding="utf-8")
    zod_fields = set(re.findall(r"^\s+([a-z_][a-z0-9_]*):", zod, flags=re.MULTILINE))
    models = (Meta, Network, MainRow, Curve, Generalisation, FairnessEntry, AblationRow, Replay, Corridor)
    for model in models:
        for name, field in model.model_fields.items():
            key = field.alias or name
            assert key in zod_fields, f"{model.__name__}.{key} is missing from schemas.mjs"
