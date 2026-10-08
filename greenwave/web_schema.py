"""Data contract between the Python pipeline and the website (spec Section 11.2).

Everything written to web/public/data/ is validated against these models first; the site
validates the same shapes with zod (web/src/lib/schema.ts). Field names are snake_case.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Headline(Strict):
    regime: str
    metric: str
    rl: float | None
    fixed: float | None
    max_pressure: float | None


class Kpi(Strict):
    key: str
    label: str
    value: float | None  # percent change, negative = reduction; None renders "pending"
    detail: str


class Meta(Strict):
    mock: bool
    profile: str
    generated_at: str
    git_sha: str
    synthetic_demand: bool
    junction_name: str
    network_source: Literal["osm", "plain"]
    sumo_version: str
    seeds: dict[str, int]
    deviations: list[str]
    headline: Headline
    kpis: list[Kpi] = Field(default_factory=list)
    honest_finding: str = ""
    reward: dict[str, float] = Field(default_factory=dict)  # chosen lambda, T, kappa
    controllers: dict[str, str] = Field(default_factory=dict)  # key -> display label


class Lane(Strict):
    id: str
    approach: str
    dir: Literal["in", "out"]
    width: float
    shape: list[tuple[float, float]]


class Signal(Strict):
    approach: str
    pos: tuple[float, float]
    angle: float
    link: int  # index into the SUMO state string that shows this approach's colour


class Network(Strict):
    bounds: tuple[float, float, float, float]
    lanes: list[Lane]
    junction_shape: list[tuple[float, float]]
    signals: list[Signal]
    approaches: list[str]
    facts: dict[str, object] = Field(default_factory=dict)


class MainRow(Strict):
    regime: str
    controller: str
    metric: str
    mean: float
    std: float
    n: int
    p_vs_fixed: float | None
    p_vs_mp: float | None


class Curve(Strict):
    steps: list[int]
    mean: list[float]
    std: list[float]
    n_seeds: int = 1


class Generalisation(Strict):
    metric: str
    regimes: list[str]
    matrix: list[list[float]]  # rows = trained on, columns = tested on
    std: list[list[float]]
    dr_row: list[float]
    dr_std: list[float] = Field(default_factory=list)
    gap_recovered_pct: float | None


class FairnessEntry(Strict):
    label: str
    regime: str
    ecdf_x: list[float]
    ecdf_y: list[float]
    p50: float
    p95: float
    max: float


class PerClassRow(Strict):
    regime: str
    controller: str
    class_: str = Field(alias="class")
    delay_mean: float
    delay_std: float

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AblationRow(Strict):
    group: str
    variant: str
    metric: str
    mean: float
    std: float
    n: int
    regime: str = "peak"
    reference: bool = False
    takeaway: str = ""


class Series(Strict):
    wait_now: list[float]
    queue_by_approach: list[list[int]]
    person_wait_cum: list[float]
    max_wait: list[float]


class ReplaySide(Strict):
    veh_class: list[int]
    frames: list[list[int]]
    signal: list[str]
    phase: list[int]
    series: Series


class SideLabel(Strict):
    controller: str
    label: str


class ReplayEvent(Strict):
    t: int
    label: str


class Replay(Strict):
    scene: str
    title: str
    caption: str
    left: SideLabel
    right: SideLabel
    regime: str
    seed: int
    t0: int
    t1: int
    dt: int
    classes: list[str]
    events: list[ReplayEvent]
    sides: dict[Literal["left", "right"], ReplaySide]
    mock: bool = False
