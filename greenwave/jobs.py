"""Training job specification shared by the trainer, the queue and the evaluator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from greenwave.config import ROOT, dr_pool_files


@dataclass
class JobSpec:
    name: str
    agent: str = "ddqn"  # ddqn | dqn | ppo
    regime: str = "peak"  # low | peak | skewed | surge | dr
    reward: str = "fair"
    lam: float | None = None
    T: float | None = None
    bus_weight: float | None = None
    steps: int = 100_000
    seed: int = 0
    delta: int | None = None
    sublane: bool = True
    obs_mask: list[str] = field(default_factory=list)
    network: str = "junction"
    group: str = "main"  # main | ablation | sweep | smoke
    family: str = ""  # job name without the seed suffix
    eval_every: int = 10_000
    smdp_discount: bool = False

    def __post_init__(self) -> None:
        if not self.family:
            self.family = self.name.rsplit("__s", 1)[0]

    @property
    def run_dir(self) -> Path:
        return ROOT / "runs" / self.name

    def reward_overrides(self) -> dict[str, Any]:
        return {"lam": self.lam, "T": self.T, "bus_weight": self.bus_weight}

    def env_kwargs(self, training: bool = True) -> dict[str, Any]:
        """Keyword arguments for SignalEnv. Evaluation passes its own regime and seed."""
        kw: dict[str, Any] = {
            "network": self.network,
            "reward": self.reward,
            "reward_overrides": self.reward_overrides(),
            "delta": self.delta,
            "sublane": self.sublane,
            "obs_mask": tuple(self.obs_mask),
        }
        if training:
            if self.regime == "dr":
                kw["route_files"] = dr_pool_files()
                kw["regime"] = "peak"
            else:
                kw["regime"] = self.regime
        return kw

    def validation_regime(self) -> str:
        return "peak" if self.regime == "dr" else self.regime

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> JobSpec:
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @classmethod
    def load(cls, path: str | Path) -> JobSpec:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def find_checkpoint(job_name: str) -> tuple[Path, Path]:
    """(config.json, weights) for a trained job: runs/ first, then the committed models."""
    run = ROOT / "runs" / job_name
    for ext in ("pt", "zip"):
        if (run / f"best.{ext}").exists() and (run / "config.json").exists():
            return run / "config.json", run / f"best.{ext}"
    models = ROOT / "results" / "models"
    for ext in ("pt", "zip"):
        if (models / f"best_{job_name}.{ext}").exists():
            return models / f"best_{job_name}.json", models / f"best_{job_name}.{ext}"
    raise FileNotFoundError(f"no checkpoint for job '{job_name}'")
