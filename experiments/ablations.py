"""Ablation table (spec 8.4) with one template-generated takeaway per question.

    python experiments/ablations.py

Also evaluates the baselines without the sub-lane model if that has not been done, since
the sub-lane ablation asks whether the ranking of controllers changes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.aggregate import (  # noqa: E402
    SUMMARY,
    ablation_rows,
    family_episodes,
    read_episodes,
    write_json,
)  # fmt: skip


def main() -> None:
    if not (SUMMARY / "episodes_baselines_nosublane.csv").exists():
        subprocess.call([sys.executable, str(ROOT / "experiments" / "evaluate.py"), "--no-sublane"], cwd=str(ROOT))
    fam = family_episodes(read_episodes("agents"))
    rows = ablation_rows(fam, read_episodes("baselines"), read_episodes("baselines_nosublane"))
    write_json("ablations.json", rows)
    if not rows:
        print("no ablation families evaluated yet")
        return
    table = pd.DataFrame(rows)
    table.to_csv(SUMMARY / "ablations.csv", index=False)
    for group, part in table.groupby("group", sort=False):
        wide = part.pivot_table(index="variant", columns="metric", values="mean", sort=False)
        print(f"\n[{group}] {part['takeaway'].iloc[0]}")
        print(wide.round(1).to_string())


if __name__ == "__main__":
    main()
