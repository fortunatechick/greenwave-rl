"""Expand configs/experiments.yaml and a compute profile into a concrete job list."""

from __future__ import annotations

import json
from typing import Any

from greenwave.config import CONFIG_DIR, ROOT, load_yaml
from greenwave.jobs import JobSpec

PROFILES = ("quick", "day", "full")
SWEEP_CHOICE = ROOT / "results" / "summary" / "sweep_choice.json"


def load_profile(name: str) -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "profiles" / f"{name}.yaml")


def sweep_choice() -> dict[str, float] | None:
    """The (lambda, T) picked by the sweep, once it has run."""
    if SWEEP_CHOICE.exists():
        chosen = json.loads(SWEEP_CHOICE.read_text(encoding="utf-8"))["chosen"]
        return {"lam": float(chosen["lam"]), "T": float(chosen["T"])}
    return None


def sweep_jobs(profile: dict[str, Any], scale: float = 1.0) -> list[JobSpec]:
    exp = load_yaml(CONFIG_DIR / "experiments.yaml")["sweep"]
    jobs = []
    for lam in exp["lambdas"]:
        for T in exp["thresholds"]:
            jobs.append(
                JobSpec(
                    name=f"sweep_l{lam:g}_T{T:g}__s0", agent="ddqn", regime=exp["regime"],
                    reward="fair", lam=float(lam), T=float(T),
                    steps=int(profile["sweep_steps"] * scale), seed=0, group="sweep",
                )  # fmt: skip
            )
    return jobs


def experiment_jobs(
    profile: dict[str, Any], scale: float = 1.0, drop_questions: tuple[str, ...] = ()
) -> list[JobSpec]:
    """Main and ablation jobs. lambda and T come from the sweep when it has been run."""
    exp = load_yaml(CONFIG_DIR / "experiments.yaml")
    choice = sweep_choice() or {}
    jobs: list[JobSpec] = []
    for group, key, steps_key, seeds_key in (
        ("main", "main", "main_steps", "seeds_main"),
        ("ablation", "ablations", "ablation_steps", "seeds_ablation"),
    ):
        for fam in exp[key]:
            if fam.get("question") in drop_questions:
                continue
            steps = int(profile[steps_key] * scale * fam.get("steps_scale", 1.0))
            for seed in range(int(profile[seeds_key])):
                jobs.append(
                    JobSpec(
                        name=f"{fam['family']}__s{seed}",
                        family=fam["family"],
                        agent=fam.get("agent", "ddqn"),
                        regime=fam.get("regime", "peak"),
                        reward=fam.get("reward", "fair"),
                        lam=choice.get("lam"),
                        T=choice.get("T"),
                        bus_weight=fam.get("bus_weight"),
                        steps=steps,
                        seed=seed,
                        delta=fam.get("delta"),
                        sublane=fam.get("sublane", True),
                        obs_mask=list(fam.get("obs_mask", [])),
                        group=group,
                    )
                )
    return jobs


def family_questions() -> dict[str, str]:
    exp = load_yaml(CONFIG_DIR / "experiments.yaml")
    return {f["family"]: f.get("question", "") for f in exp["ablations"]}


def job_cores(spec: JobSpec) -> int:
    """CPU cores a job occupies: PPO runs 4 simulations plus a validation process."""
    return 4 if spec.agent == "ppo" else 1
