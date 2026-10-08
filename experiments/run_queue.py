"""Training job queue: resumable, core-aware, one process and one log per job.

    python experiments/run_queue.py --plan runs/plan.json --workers 7

Stages: lambda/T sweep -> pick -> main runs (peak Double DQN first) -> ablations.
Jobs with runs/<job>/done.flag are skipped, so the queue can be restarted at any time.
Progress goes to runs/status.json, logs/queue.log and the queue block of PROGRESS.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.jobs import JobSpec  # noqa: E402
from greenwave.plan import experiment_jobs, job_cores, load_profile, sweep_jobs  # noqa: E402

STATUS = ROOT / "runs" / "status.json"
LOGS = ROOT / "logs"
MAX_ATTEMPTS = 2


def order_key(spec: JobSpec) -> tuple[int, int, str]:
    """Peak Double DQN first, then the other main runs, DR, SB3 agents, then ablations."""
    if spec.group == "main":
        if spec.family == "ddqn_fair__peak":
            rank = 0
        elif spec.agent == "ddqn" and spec.regime != "dr":
            rank = 1
        elif spec.regime == "dr":
            rank = 2
        else:
            rank = 3
    else:
        rank = 4
    return (rank, spec.seed, spec.name)


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOGS / "queue.log", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def write_status(status: dict[str, Any]) -> None:
    STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
    jobs = status["jobs"]
    counts: dict[str, int] = {}
    for j in jobs.values():
        counts[j["state"]] = counts.get(j["state"], 0) + 1
    lines = [
        f"Profile `{status['profile']}` - updated {time.strftime('%Y-%m-%d %H:%M')} - "
        + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())),
        "",
        "| Job | State | Steps | Minutes | Best validation score |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, j in jobs.items():
        minutes = f"{j['minutes']:.1f}" if j.get("minutes") else ""
        score = f"{j['best_val_score']:.4f}" if j.get("best_val_score") is not None else ""
        lines.append(f"| {name} | {j['state']} | {j['steps']} | {minutes} | {score} |")
    progress = ROOT / "PROGRESS.md"
    if progress.exists():
        text = progress.read_text(encoding="utf-8")
        block = "<!-- queue:start -->\n" + "\n".join(lines) + "\n<!-- queue:end -->"
        pattern = re.compile(r"<!-- queue:start -->.*?<!-- queue:end -->", re.DOTALL)
        if pattern.search(text):
            progress.write_text(pattern.sub(lambda _: block, text), encoding="utf-8")


def launch(spec: JobSpec) -> subprocess.Popen:
    spec.run_dir.mkdir(parents=True, exist_ok=True)
    cfg = spec.run_dir / "config.json"
    cfg.write_text(spec.to_json(), encoding="utf-8")
    env = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PYTHONUNBUFFERED": "1"}
    out = open(LOGS / f"{spec.name}.log", "a", encoding="utf-8")  # noqa: SIM115
    proc = subprocess.Popen(
        [sys.executable, "-m", "greenwave.train", "--config", str(cfg)],
        cwd=str(ROOT), env=env, stdout=out, stderr=subprocess.STDOUT,
    )  # fmt: skip
    with open(LOGS / "pids.txt", "a", encoding="utf-8") as fh:
        fh.write(f"{proc.pid} {spec.name}\n")
    return proc


def run_stage(jobs: list[JobSpec], workers: int, status: dict[str, Any]) -> None:
    pending = sorted(jobs, key=order_key)
    for spec in pending:
        done = (spec.run_dir / "done.flag").exists()
        entry = status["jobs"].setdefault(spec.name, {"steps": spec.steps, "group": spec.group})
        entry["state"] = "done" if done else "pending"
        if done and (spec.run_dir / "result.json").exists():
            result = json.loads((spec.run_dir / "result.json").read_text(encoding="utf-8"))
            entry["best_val_score"] = result.get("best_val_score")
            entry["minutes"] = result.get("wall_s", 0) / 60.0
    pending = [s for s in pending if status["jobs"][s.name]["state"] == "pending"]
    write_status(status)

    running: dict[str, tuple[subprocess.Popen, JobSpec, float]] = {}
    attempts: dict[str, int] = {}
    free = workers
    while pending or running:
        for spec in list(pending):
            cores = min(job_cores(spec), workers)
            if cores <= free:
                pending.remove(spec)
                attempts[spec.name] = attempts.get(spec.name, 0) + 1
                running[spec.name] = (launch(spec), spec, time.time())
                free -= cores
                status["jobs"][spec.name]["state"] = "running"
                log(f"start {spec.name} ({spec.steps} steps)")
        write_status(status)

        time.sleep(5)
        for name, (proc, spec, started) in list(running.items()):
            code = proc.poll()
            if code is None:
                continue
            del running[name]
            free += min(job_cores(spec), workers)
            minutes = (time.time() - started) / 60.0
            entry = status["jobs"][name]
            if code == 0 and (spec.run_dir / "done.flag").exists():
                result = json.loads((spec.run_dir / "result.json").read_text(encoding="utf-8"))
                entry.update(state="done", minutes=minutes, best_val_score=result["best_val_score"])
                left = len(pending) + len(running)
                log(f"done  {name} in {minutes:.1f} min, best validation score "
                    f"{result['best_val_score']:.4f} ({left} jobs left)")  # fmt: skip
            elif attempts[name] < MAX_ATTEMPTS:
                log(f"FAIL  {name} (exit {code}), retrying once")
                pending.insert(0, spec)
                entry["state"] = "pending"
            else:
                entry.update(state="failed", minutes=minutes)
                log(f"FAIL  {name} (exit {code}) twice, giving up; see logs/{name}.log")
        write_status(status)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default=str(ROOT / "runs" / "plan.json"))
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--stage", choices=["all", "sweep", "experiments"], default="all")
    args = parser.parse_args()
    LOGS.mkdir(exist_ok=True)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    workers = args.workers or plan["workers"]
    profile = load_profile(plan["profile"])
    scale = plan.get("scale", 1.0)
    drop = tuple(plan.get("dropped_questions", []))
    status: dict[str, Any] = {"profile": plan["profile"], "workers": workers, "jobs": {}}
    if STATUS.exists():
        status["jobs"] = json.loads(STATUS.read_text(encoding="utf-8")).get("jobs", {})
    log(f"queue start: profile {plan['profile']} scale {scale} on {workers} workers")

    if args.stage in ("all", "sweep"):
        run_stage(sweep_jobs(profile, scale), workers, status)
        code = subprocess.call(
            [sys.executable, str(ROOT / "experiments" / "pick_sweep.py"), "--workers", str(workers)],
            cwd=str(ROOT),
        )
        log(f"sweep choice written (exit {code})")
    if args.stage in ("all", "experiments"):
        # Built after the sweep so every job carries the chosen lambda and T.
        run_stage(experiment_jobs(profile, scale, drop), workers, status)
    failed = [n for n, j in status["jobs"].items() if j["state"] == "failed"]
    log(f"queue finished; {len(failed)} failed job(s) {failed if failed else ''}")


if __name__ == "__main__":
    main()
