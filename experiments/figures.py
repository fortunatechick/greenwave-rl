"""Every report figure, from results/summary/ (PNG at 200 dpi + SVG, site palette).

    python experiments/figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.export_web import archive_models, curves, fairness  # noqa: E402
from greenwave.aggregate import CONTROLLER_LABELS, SUMMARY  # noqa: E402
from greenwave.config import CLASSES, REGIMES, load_cfg  # noqa: E402
from greenwave.netjson import network_json  # noqa: E402
from greenwave.plan import sweep_choice  # noqa: E402

FIG = ROOT / "report" / "figures"
BG, SURFACE, LINE, TEXT, MUTED = "#0A0C0F", "#111419", "#252A32", "#E8EAED", "#8A93A0"
GO, AMBER, STOP, WAVE = "#3DDC84", "#FFB020", "#FF4D4F", "#2BD4C8"
CLASS_COLOURS = {"two_wheeler": "#7DD3FC", "auto_rickshaw": "#FDE047", "car": "#CBD5E1", "bus": "#C4B5FD"}
SERIES = [WAVE, "#C4B5FD", AMBER, "#7DD3FC", MUTED, STOP]
ORDER = ["fixed_peak", "fixed_matched", "actuated", "max_pressure", "dqn_sb3", "ppo", "ddqn_fair", "ddqn_fair_dr"]
OURS = {"ddqn_fair", "ddqn_fair_dr"}


def style() -> None:
    sns.set_theme(style="darkgrid")
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": SURFACE, "savefig.facecolor": BG,
        "axes.edgecolor": LINE, "grid.color": LINE, "grid.linestyle": ":", "text.color": TEXT,
        "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlecolor": TEXT,
        "font.size": 10, "axes.titlesize": 11, "legend.frameon": False, "figure.dpi": 100,
    })  # fmt: skip


def save(fig: plt.Figure, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}")


def short(key: str) -> str:
    return CONTROLLER_LABELS.get(key, key).split(" (")[0].replace(", fair reward", "").replace(", SB3", "")


def fig_main(table: pd.DataFrame, metric: str, ylabel: str, name: str) -> None:
    sel = table[table.metric == metric]
    keys = [k for k in ORDER if k in set(sel.controller)]
    fig, axes = plt.subplots(1, len(REGIMES), figsize=(13, 3.6), sharey=False)
    for ax, regime in zip(axes, REGIMES, strict=True):
        part = sel[sel.regime == regime].set_index("controller").reindex(keys).dropna(subset=["mean"])
        colours = [WAVE if k in OURS else MUTED for k in part.index]
        ax.bar(range(len(part)), part["mean"], yerr=part["std"], color=colours, ecolor=TEXT, capsize=2, width=0.7)
        ax.set_xticks(range(len(part)), [short(k) for k in part.index], rotation=55, ha="right", fontsize=8)
        ax.set_title(regime)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel(ylabel)
    fig.suptitle(f"{ylabel} by controller and regime (mean ± std over evaluation seeds)", y=1.03, color=TEXT)
    save(fig, name)


def fig_curves() -> None:
    data = curves()
    if not data:
        return
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for i, (key, c) in enumerate(data.items()):
        steps, mean, std = np.array(c["steps"]), np.array(c["mean"]), np.array(c["std"])
        ax.plot(steps, mean, color=SERIES[i], lw=2, label=f"{short(key)} ({c['n_seeds']} seeds)")
        ax.fill_between(steps, mean - std, mean + std, color=SERIES[i], alpha=0.16, lw=0)
    ax.set_xlabel("training steps (decisions)")
    ax.set_ylabel("validation score (higher is better)")
    ax.set_title("Learning curves, peak regime")
    ax.legend()
    save(fig, "learning_curves")


def fig_generalisation() -> None:
    path = SUMMARY / "generalisation.json"
    if not path.exists():
        return
    for g in json.loads(path.read_text(encoding="utf-8")):
        rows = [*g["matrix"], *([g["dr_row"]] if g["dr_row"] else [])]
        labels = [*g["regimes"], *(["randomised"] if g["dr_row"] else [])]
        fig, ax = plt.subplots(figsize=(5.2, 4.2))
        cmap = sns.diverging_palette(145, 12, s=80, l=45, as_cmap=True)
        sns.heatmap(np.array(rows), annot=True, fmt=".1f", cmap=cmap,
                    center=g["diagonal_mean"], xticklabels=g["regimes"], yticklabels=labels, linewidths=2,
                    linecolor=BG, cbar_kws={"label": g["metric"]}, ax=ax)  # fmt: skip
        ax.set_xlabel("tested on")
        ax.set_ylabel("trained on")
        gap = "n/a" if g["gap_recovered_pct"] is None else f"{g['gap_recovered_pct']:.0f}%"
        ax.set_title(f"Generalisation: {g['metric']} (gap recovered by DR: {gap})")
        save(fig, f"generalisation_{g['metric']}")


def fig_fairness() -> None:
    data = fairness()
    regimes = sorted({e["regime"] for e in data.values()})
    if not regimes:
        return
    T = (sweep_choice() or {}).get("T", load_cfg()["rewards"]["T"])
    fig, axes = plt.subplots(1, len(regimes), figsize=(6.2 * len(regimes), 3.8), squeeze=False)
    for ax, regime in zip(axes[0], regimes, strict=True):
        for i, e in enumerate(v for v in data.values() if v["regime"] == regime):
            ax.plot(e["ecdf_x"], e["ecdf_y"], color=SERIES[i % len(SERIES)], lw=2 if i == 0 else 1.4,
                    label=f"{e['label']} (p95 {e['p95']:.0f} s, max {e['max']:.0f} s)")  # fmt: skip
        ax.axvline(T, color=AMBER, ls="--", lw=1)
        ax.set_xlabel("waiting time per vehicle (s)")
        ax.set_ylabel("share of vehicles")
        ax.set_title(f"Per-vehicle wait, {regime} regime (T = {T:g} s)")
        ax.legend(fontsize=7.5, loc="lower right")
    save(fig, "fairness_ecdf")


def fig_per_class(table: pd.DataFrame) -> None:
    keys = [k for k in ORDER if k in set(table.controller)]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    width = 0.2
    for i, c in enumerate(CLASSES):
        part = table[(table.metric == f"delay_{c}") & (table.regime == "peak")].set_index("controller").reindex(keys)
        ax.bar(np.arange(len(keys)) + (i - 1.5) * width, part["mean"], width, yerr=part["std"],
               color=CLASS_COLOURS[c], ecolor=TEXT, capsize=1.5, label=c.replace("_", "-"))  # fmt: skip
    ax.set_xticks(range(len(keys)), [short(k) for k in keys], rotation=25, ha="right")
    ax.set_ylabel("delay per vehicle (s)")
    ax.set_title("Delay by vehicle class, peak regime")
    ax.grid(axis="x", visible=False)
    ax.legend(ncols=4)
    save(fig, "per_class_delay")


def fig_ablations() -> None:
    path = SUMMARY / "ablations.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if not rows:
        return
    df = pd.DataFrame(rows)
    groups = list(dict.fromkeys(df["group"]))
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.5))
    for ax, group in zip(axes.flat, groups, strict=False):
        part = df[(df.group == group) & (df.metric == "person_wait")]
        colours = [WAVE if r else MUTED for r in part["reference"]]
        ax.barh(range(len(part)), part["mean"], xerr=part["std"], color=colours, ecolor=TEXT, capsize=2)
        ax.set_yticks(range(len(part)), part["variant"], fontsize=8)
        ax.invert_yaxis()
        ax.set_title(f"{group} ({part['regime'].iloc[0]})")
        ax.set_xlabel("wait per person (s)")
        ax.grid(axis="y", visible=False)
    for ax in axes.flat[len(groups):]:
        ax.axis("off")
    fig.suptitle("Ablations: wait per person, reference in green", color=TEXT)
    fig.tight_layout()
    save(fig, "ablations")


def fig_network() -> None:
    net = network_json()
    fig, ax = plt.subplots(figsize=(5, 5))
    for lane in net["lanes"]:
        xs, ys = zip(*lane["shape"], strict=True)
        ax.plot(xs, ys, color="#343B46", lw=lane["width"] * 2.1, solid_capstyle="butt")
        ax.plot(xs, ys, color="#1B2027", lw=lane["width"] * 1.9, solid_capstyle="butt")
    jx, jy = zip(*net["junction_shape"], strict=True)
    ax.fill(jx, jy, color="#1B2027")
    for s in net["signals"]:
        ax.text(s["pos"][0] * 5.5, s["pos"][1] * 5.5, s["approach"], color=TEXT, ha="center", va="center", fontsize=13)
    ax.set_xlim(-90, 90)
    ax.set_ylim(-90, 90)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor(BG)
    FIG.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)
    fig.savefig(ROOT / "docs" / "network.png", dpi=200, bbox_inches="tight")
    save(fig, "network")


def main() -> None:
    style()
    archive_models()
    print("figures:")
    fig_network()
    table_path = SUMMARY / "main_table.csv"
    if not table_path.exists():
        print("main_table.csv missing; only the network figure was drawn")
        return
    table = pd.read_csv(table_path)
    fig_main(table, "person_wait", "wait per person (s)", "main_person_wait")
    fig_main(table, "max_wait", "max wait (s)", "main_max_wait")
    fig_main(table, "co2", "CO2 per vehicle (g)", "co2")
    fig_curves()
    fig_generalisation()
    fig_fairness()
    fig_per_class(table)
    fig_ablations()


if __name__ == "__main__":
    main()
