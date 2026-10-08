"""Cross-platform task runner. The Makefile delegates here, so `make <target>` and
`python tasks.py <target>` are the same thing (GNU make is not standard on Windows).

    python tasks.py all      # regenerate every result, figure, replay and the web data
                             # from the saved checkpoints
    python tasks.py train    # budget planner + training queue (hours)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
NPM = shutil.which("npm") or "npm"
WEB = ROOT / "web"

Step = tuple[list[str], Path]


def py(*args: str) -> Step:
    return ([PY, *args], ROOT)


def npm(*args: str) -> Step:
    return ([NPM, *args], WEB)


TARGETS: dict[str, list[Step | str]] = {
    "setup": [py("-m", "pip", "install", "-r", "requirements.txt")],
    "network": [py("network/build_network.py"), py("network/build_network.py", "--toy")],
    "demand": [py("demand/generate.py")],
    "toy": [py("experiments/toy_sanity.py")],
    "baselines": [py("experiments/evaluate.py", "--baselines")],
    "bench": [py("experiments/budget.py")],
    "train": ["bench", py("experiments/run_queue.py")],
    "eval": [
        py("experiments/evaluate.py", "--agents"),
        py("experiments/generalisation.py"),
        py("experiments/ablations.py"),
    ],
    "figures": [py("experiments/figures.py")],
    "replays": [py("experiments/record_replay.py")],
    "export": [py("experiments/export_web.py"), py("report/fill.py"), py("experiments/make_readme_gif.py")],
    "web-dev": [npm("run", "dev")],
    "web-build": [npm("run", "build")],
    "demo": [py("demo/side_by_side.py")],
    "test": [py("-m", "ruff", "check", "."), py("-m", "pytest", "-q")],
    "all": ["network", "demand", "baselines", "eval", "figures", "replays", "export"],
}


def run(target: str) -> None:
    if target not in TARGETS:
        sys.exit(f"unknown target '{target}'. Targets: {' '.join(TARGETS)}")
    for step in TARGETS[target]:
        if isinstance(step, str):
            run(step)
            continue
        cmd, cwd = step
        print(f"\n>> {' '.join(cmd[1:] if cmd[0] == PY else cmd)}", flush=True)
        env = {**os.environ, "PYTHONPATH": str(ROOT)}
        code = subprocess.call(cmd, cwd=str(cwd), env=env, shell=(cmd[0] == NPM and os.name == "nt"))
        if code != 0:
            sys.exit(code)


if __name__ == "__main__":
    for name in sys.argv[1:] or ["all"]:
        run(name)
