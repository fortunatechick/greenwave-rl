"""Main table and generalisation study from the evaluation episodes.

    python experiments/generalisation.py

Reads results/summary/episodes_{baselines,agents}.csv and writes:
    family_episodes.csv   RL metrics per (family, regime, eval seed), averaged over training seeds
    main_table.csv        every controller x regime x metric, mean / std / n / Welch p-values
    generalisation.json   4 x 4 train-on / test-on grids, the DR row and the gap recovered
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.aggregate import (  # noqa: E402
    SUMMARY,
    family_episodes,
    generalisation,
    main_rows,
    read_episodes,
    write_json,
)  # fmt: skip


def main() -> None:
    base = read_episodes("baselines")
    fam = family_episodes(read_episodes("agents"))
    fam.to_csv(SUMMARY / "family_episodes.csv", index=False)

    rows = main_rows(base, fam)
    table = pd.DataFrame(rows)
    table.to_csv(SUMMARY / "main_table.csv", index=False)
    wide = table[table.metric == "person_wait"].pivot(index="controller", columns="regime", values="mean")
    print("wait per person (s):")
    print(wide.round(1).to_string())

    grids = [g for m in ("person_wait", "max_wait") if (g := generalisation(fam, m))]
    write_json("generalisation.json", grids)
    for g in grids:
        gap = "n/a" if g["gap_recovered_pct"] is None else f"{g['gap_recovered_pct']:.0f}%"
        print(f"\n{g['metric']}: diagonal {g['diagonal_mean']:.1f}, off-diagonal {g['off_diagonal_mean']:.1f}, "
              f"gap recovered by DR {gap}")  # fmt: skip
        print(pd.DataFrame(g["matrix"], index=g["regimes"], columns=g["regimes"]).round(1).to_string())
        if g["dr_row"]:
            print("DR   ", [round(v, 1) for v in g["dr_row"]])
    if not grids:
        print("generalisation grids pending: not every regime-matched family has been evaluated")


if __name__ == "__main__":
    main()
