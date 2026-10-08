"""Write report/REPORT.md, report/slides.md and report/viva.md.

    python report/fill.py

Every number is read from results/summary/ and web/public/data/meta.json; nothing in the
generated files is typed by hand. Re-run after `python tasks.py eval export`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenwave.aggregate import CONTROLLER_LABELS, SUMMARY  # noqa: E402
from greenwave.config import CLASSES, REGIMES, load_cfg  # noqa: E402

OUT = ROOT / "report"
ORDER = ["fixed_peak", "fixed_matched", "actuated", "max_pressure", "random", "dqn_sb3", "ppo", "ddqn_fair",
         "ddqn_fair_dr"]  # fmt: skip
METRICS = [("person_wait", "Wait / person (s)", 1), ("veh_wait", "Wait / vehicle (s)", 1),
           ("avg_queue", "Avg queue (veh)", 1), ("throughput", "Throughput (veh/h)", 0),
           ("max_wait", "Max wait (s)", 0), ("wait_p95", "Wait p95 (s)", 0), ("co2", "CO2 (g/veh)", 0)]  # fmt: skip
QUESTIONS = {
    "reward": "Which objective produces the best real behaviour?",
    "fairness": "Does the agent starve the minor road without the fairness penalty?",
    "weighting": "Do buses clear faster with passenger weighting, and at what cost to others?",
    "bus_weight": "How sensitive are results to the bus occupancy assumption?",
    "state": "Which observations matter?",
    "interval": "Decision interval: reactivity against stability",
    "sublane": "Does modelling mixed traffic change the ranking of controllers?",
}


def md_table(head: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "| " + " | ".join("---" for _ in head) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def main_table(table: pd.DataFrame, regime: str) -> str:
    part = table[table.regime == regime]
    rows = []
    for key in ORDER:
        sel = part[part.controller == key]
        if sel.empty:
            continue
        cells = [CONTROLLER_LABELS.get(key, key)]
        for metric, _, digits in METRICS:
            r = sel[sel.metric == metric]
            if r.empty:
                cells.append("–")
                continue
            r = r.iloc[0]
            best = part[part.metric == metric]["mean"]
            is_best = r["mean"] == (best.max() if metric == "throughput" else best.min())
            value = f"{r['mean']:.{digits}f} ± {r['std']:.{digits}f}"
            star = "*" if pd.notna(r["p_vs_fixed"]) and r["p_vs_fixed"] < 0.05 else ""
            dagger = "†" if pd.notna(r["p_vs_mp"]) and r["p_vs_mp"] < 0.05 else ""
            cells.append((f"**{value}**" if is_best else value) + star + dagger)
        rows.append(cells)
    return md_table(["Controller", *[m[1] for m in METRICS]], rows)


def val(table: pd.DataFrame, regime: str, controller: str, metric: str) -> float | None:
    sel = table[(table.regime == regime) & (table.controller == controller) & (table.metric == metric)]
    return None if sel.empty else float(sel.iloc[0]["mean"])


def f(x: float | None, digits: int = 1, unit: str = "") -> str:
    return "n/a" if x is None else f"{x:.{digits}f}{unit}"


def load_json(path: Path, default):  # noqa: ANN001, ANN201
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main() -> None:
    cfg = load_cfg()
    table_path = SUMMARY / "main_table.csv"
    if not table_path.exists():
        sys.exit("results/summary/main_table.csv missing: run the evaluation first")
    table = pd.read_csv(table_path)
    meta = load_json(ROOT / "web" / "public" / "data" / "meta.json", {})
    if meta.get("mock"):
        sys.exit("web/public/data/meta.json is mock data: run experiments/export_web.py first")
    gens = load_json(SUMMARY / "generalisation.json", [])
    ablations = pd.DataFrame(load_json(SUMMARY / "ablations.json", []))
    sweep = load_json(SUMMARY / "sweep_choice.json", {})
    toy = load_json(SUMMARY / "toy_sanity.json", {})
    demand = load_json(ROOT / "demand" / "demand_meta.json", {})
    reward = meta.get("reward", {})
    lam, T = reward.get("lambda", cfg["rewards"]["lambda"]), reward.get("T", cfg["rewards"]["T"])
    seeds = meta.get("seeds", {})
    d = cfg["demand"]

    main_tables = "\n\n".join(f"**{r.title()} regime**\n\n{main_table(table, r)}" for r in REGIMES)

    gen_text = []
    for g in gens:
        head = ["Trained on \\ tested on", *g["regimes"]]
        rows = [[g["regimes"][i], *[f"{v:.1f}" for v in row]] for i, row in enumerate(g["matrix"])]
        if g["dr_row"]:
            rows.append(["**randomised (DR)**", *[f"**{v:.1f}**" for v in g["dr_row"]]])
        gap = "not defined" if g["gap_recovered_pct"] is None else f"{g['gap_recovered_pct']:.0f}%"
        gen_text.append(
            f"**{g['metric']}** (diagonal mean {g['diagonal_mean']:.1f}, off-diagonal mean "
            f"{g['off_diagonal_mean']:.1f}, gap recovered by DR: {gap})\n\n{md_table(head, rows)}"
        )
    gen_block = "\n\n".join(gen_text) or "_Generalisation grids pending._"

    abl_text = []
    if not ablations.empty:
        for group, part in ablations.groupby("group", sort=False):
            variants = list(dict.fromkeys(part["variant"]))
            rows = []
            for v in variants:
                cells = [v + (" (reference)" if part[part.variant == v]["reference"].iloc[0] else "")]
                for metric in ("person_wait", "max_wait", "delay_bus"):
                    r = part[(part.variant == v) & (part.metric == metric)]
                    cells.append("–" if r.empty else f"{r.iloc[0]['mean']:.1f} ± {r.iloc[0]['std']:.1f}")
                rows.append(cells)
            abl_text.append(
                f"**{QUESTIONS.get(group, group)}** ({part['regime'].iloc[0]} regime)\n\n"
                f"{md_table(['Variant', 'Wait / person (s)', 'Max wait (s)', 'Bus delay (s)'], rows)}\n\n"
                f"{part['takeaway'].iloc[0]}"
            )
    abl_block = "\n\n".join(abl_text) or "_Ablations pending._"

    sweep_block = "_Sweep not run; defaults used._"
    if sweep:
        rows = [[f"{r['lam']:g}", f"{r['T']:g}", f"{r['person_wait']:.1f}", f"{r['max_wait']:.0f}",
                 "yes" if r["feasible"] else "no"] for r in sweep["table"]]  # fmt: skip
        sweep_block = (
            md_table(["lambda", "T (s)", "Wait / person (s)", "Max wait (s)", "max wait <= 1.2 T"], rows)
            + f"\n\nRule: {sweep['rule']}. Chosen: lambda = {sweep['chosen']['lam']:g}, T = {sweep['chosen']['T']:g} s."
        )

    demand_rows = []
    for regime in REGIMES:
        r = demand.get("regimes", {}).get(regime)
        if r:
            demand_rows.append([regime, f"{sum(r['veh_per_hour_by_class'].values()):.0f}",
                                f"{r['webster']['cycle']:.0f}", str(list(r["webster"]["greens"].values())),
                                f"{max(r['webster']['saturation'].values()):.2f}"])  # fmt: skip
    demand_block = md_table(["Regime", "veh/h", "Webster cycle (s)", "Greens N,E,S,W (s)", "Max degree of saturation"],
                            demand_rows)  # fmt: skip

    deviations = "\n".join(f"- {x}" for x in meta.get("deviations", [])) or "- None recorded."
    def kpi_value(value: float | None) -> str:
        return "pending" if value is None else f"{value:+.0f}%"

    kpis = "\n".join(f"- {k['label']}: **{kpi_value(k['value'])}** ({k['detail']})" for k in meta.get("kpis", []))
    synthetic = ("Demand is **synthetic**: no vehicles were counted at a real junction."
                 if meta.get("synthetic_demand") else "Demand is scaled from field counts.")  # fmt: skip
    toy_line = ""
    if toy:
        import numpy as np

        toy_line = (f"On the toy junction the scratch Double DQN reached a mean wait of "
                    f"{np.mean(toy['veh_wait']['toy_ddqn']):.0f} s per vehicle against "
                    f"{np.mean(toy['veh_wait']['random']):.0f} s for a random policy within 20k steps.")  # fmt: skip
    rl_s, fx_s, mp_s = (val(table, "surge", c, "person_wait") for c in ("ddqn_fair", "fixed_matched", "max_pressure"))
    stale = "; ".join(
        f"{r}: {f(val(table, r, 'fixed_peak', 'person_wait'))} s vs {f(val(table, r, 'fixed_matched', 'person_wait'))} s"
        for r in REGIMES if r != "peak"
    )  # fmt: skip

    report = f"""# GreenWave-RL: Fairness-Aware Deep Reinforcement Learning for Adaptive Signal Control under Mixed Indian Traffic

_Generated by `report/fill.py` from `results/summary/` (build {meta.get('git_sha', '?')}, {meta.get('generated_at', '')[:10]},
compute profile `{meta.get('profile', '?')}`). Do not edit numbers by hand; re-run the script._

## Abstract

Fixed-time traffic signals cannot respond to demand that changes by the minute. This project builds a microscopic
simulation of a signalised four-arm junction populated with mixed traffic (two-wheelers, auto-rickshaws, cars, buses)
and trains deep reinforcement learning agents to choose signal phases from live queue observations. Double DQN
(written from scratch), DQN and PPO are compared against fixed-time, actuated and max-pressure controllers across four
demand regimes. The contribution is a passenger-weighted reward with a fairness penalty that keeps the agent from
starving low-volume approaches, and a measurement of how well policies trained on one demand pattern survive on
another, with and without domain randomisation.

Headline numbers:

{kpis}

{meta.get('honest_finding', '')}

## 1. Introduction

Signal timing plans are tuned by hand for an average hour and go stale. Indian traffic is mixed and weakly
lane-disciplined, which most published RL signal work ignores. Counting vehicles equally undervalues a bus carrying
{d['passenger_weights']['bus']:.0f} people against a car carrying {d['passenger_weights']['car']:.0f}. And an agent
that minimises average delay can learn to hold a minor road on red indefinitely, which a deployable controller must
not do.

**Problem statement.** Given a signalised junction with time-varying, heterogeneous traffic, learn a phase-selection
policy that minimises delay per person, keeps the worst-case wait bounded, and stays effective when demand shifts
away from what it was trained on.

**Contributions.** (1) A passenger-weighted waiting-time reward with a maximum-wait fairness penalty. (2) A
left-hand-traffic setting with four vehicle classes, sub-lane movement, free left turns and approach-wise split
phasing. (3) A generalisation study that reports failures and measures what domain randomisation recovers.

## 2. Related work

Reinforcement learning for signal control is well studied. DQN (Mnih et al., 2015) and Double DQN (van Hasselt et
al., 2016) are the value-based methods used here; PPO (Schulman et al., 2017) is the policy-gradient comparison.
IntelliLight and PressLight (Wei et al., 2018, 2019) apply deep RL to signals; PressLight builds on max-pressure
control (Varaiya, 2013), which is throughput-optimal under idealised assumptions and is kept as a baseline in every
table of this report. Ault and Sharon (2021) argue for benchmarking RL signal controllers against strong classical
baselines, which is the stance taken here. SUMO (Lopez et al., 2018) is the simulator. PCU factors follow IRC:106-1990
style values. These references are listed from memory and must be checked before citing.

## 3. Method

### 3.1 Decision process

| Element | Definition |
| --- | --- |
| State | Per incoming lane: PCU-weighted halting queue and PCU density over lane capacity. Plus current green approach (one-hot), time since last change over maximum green, and longest accumulated wait per approach over T. |
| Action | The approach to serve next; choosing the current one extends its green by {cfg['sim']['decision_interval']} s. |
| Safety | Minimum green {cfg['sim']['min_green']} s, yellow {cfg['sim']['yellow']} s on every change, maximum green {cfg['sim']['max_green']} s. Enforced by the environment, never learned. |
| Reward | Passenger-weighted reduction in accumulated waiting time minus a fairness penalty (below). |
| Episode | {cfg['sim']['episode_seconds']} simulated seconds, gamma = 0.99 per decision. The end is a truncation, so the last state is bootstrapped. |

Transitions last 5 s (extend), 13 s (yellow plus minimum green) or 18 s (a forced switch at maximum green). A
constant discount per decision is used: a semi-MDP simplification.

### 3.2 Reward

$$r_t = \\frac{{1}}{{\\kappa}}\\sum_c w_c\\,(W_{{c,t-1}} - W_{{c,t}}) - \\lambda\\,\\frac{{\\max(0,\\ \\max_a \\text{{wait}}_a - T)}}{{T}}$$

with kappa = {reward.get('kappa', 100):g}, lambda = {lam:g} and T = {T:g} s. Passenger weights (assumptions):
{', '.join(f"{c.replace('_', '-')} {d['passenger_weights'][c]:g}" for c in CLASSES)}. In the reward the weights are
divided by the mean occupancy of the traffic mix ({reward.get('mean_occupancy', 0):.3f}), which preserves their ratios
and gives the passenger-weighted reward the scale of the vehicle-count reward.

lambda and T were chosen by a sweep of nine short runs on the skewed regime, scored on seeds that are used neither for
training nor for evaluation:

{sweep_block}

### 3.3 Agents

- **Double DQN (main agent), from scratch in PyTorch.** MLP 128-128, replay buffer 50k, batch 64, Adam, epsilon 1.0
  to 0.05 over the first half of training, Huber loss, gradient-norm clip 10. Target
  `y = r + gamma (1 - d) Q_target(s', argmax_a Q_online(s', a))` with `d = 1` only on true termination.
- **DQN (Stable-Baselines3).** Vanilla DQN, not Double DQN, with matching network and schedule.
- **PPO (Stable-Baselines3).** Four parallel simulations, 512 steps per rollout.

{toy_line}

### 3.4 Baselines

Fixed-time with Webster's cycle length `C0 = (1.5 L + 5) / (1 - Y)` in two variants (a plan computed for each regime,
and the peak plan applied everywhere), SUMO's actuated controller (10 to 60 s, 3 s gap), max-pressure, and a random
phase policy. All run through the same environment and metric code.

## 4. Experimental setup

Junction: {meta.get('junction_name', '')}; geometry from {'OpenStreetMap' if meta.get('network_source') == 'osm' else 'plain XML simplified to lane counts'}.
SUMO {meta.get('sumo_version', '')} with the sub-lane model. {synthetic}

{demand_block}

Class mix by count: {', '.join(f"{c.replace('_', '-')} {d['class_mix'][c] * 100:.0f}%" for c in CLASSES)}. Turn split:
left 25 %, through 55 %, right 20 %. Arrivals are Poisson.

Evaluation: policies are frozen (epsilon = 0), {seeds.get('eval', 10)} evaluation seeds per regime, never used in
training. RL rows average {seeds.get('train', '?')} independently trained policies per evaluation seed. Tables show
mean ± standard deviation over evaluation seeds.

## 5. Results

### 5.1 Main comparison

`*` marks p < 0.05 against fixed-time (matched plan) and `†` against max-pressure (Welch's t-test). Bold is the best
value in a column.

{main_tables}

In the surge regime the regime-matched Double DQN reaches {f(rl_s)} s of waiting per person, against {f(fx_s)} s for
the matched fixed-time plan and {f(mp_s)} s for max-pressure. The stale peak plan against the matched plan, wait per
person: {stale}.

![Wait per person](figures/main_person_wait.png)

### 5.2 Learning curves

![Learning curves](figures/learning_curves.png)

### 5.3 Generalisation and domain randomisation

{gen_block}

![Generalisation](figures/generalisation_person_wait.png)

### 5.4 Fairness

![Fairness ECDF](figures/fairness_ecdf.png)

### 5.5 Ablations

Each ablation is trained with the ablation budget and compared with a reference trained with the same budget.

{abl_block}

## 6. Discussion

{meta.get('honest_finding', '')}

Max-pressure needs no training and is throughput-optimal under idealised assumptions, so on a single isolated
junction there is limited room for a learned policy to improve on it. Where the learned policy differs is in what it
optimises: people rather than vehicles, and a bound on the worst wait. The tables above show what that costs and
buys in each regime.

## 7. Limitations

- Nothing has run on a street: sensing errors, driver behaviour, pedestrians and safety certification are out of scope.
- The agent reads exact queues and waits from the simulator.
- Constant discount per decision although decisions last 5 to 18 s.
- One isolated junction, so no downstream spill-back or coordination.
- {synthetic} Occupancy weights are assumptions.

### Deviations from the build specification

{deviations}

## 8. Future work

A corridor of three to five junctions with coordinated multi-agent control; bus and emergency-vehicle priority as
explicit objectives; camera-based state estimation; pedestrian phases.

## References

Sutton and Barto, _Reinforcement Learning: An Introduction_. Mnih et al. (2015). van Hasselt et al. (2016). Schulman
et al. (2017). Varaiya (2013). Wei et al. (2018, 2019). Ault and Sharon (2021). Lopez et al. (2018). IRC:106-1990;
IRC:SP:41. Listed from memory; confirm titles, years and IRC values before citing.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")

    slides = f"""# GreenWave-RL: slide outline (12 slides, 8-minute demo)

_Numbers filled by `report/fill.py`._

1. **Title.** GreenWave-RL: fairness-aware deep RL for signal control under mixed Indian traffic.
2. **The problem.** Plans go stale; traffic is mixed; a bus is not a car; averages can starve a minor road.
3. **The junction.** {meta.get('junction_name', '')}. Left-hand traffic, four classes, split phasing. {synthetic} _(Demo: /junction, 1 min)_
4. **The decision process.** State, action, constraints in the environment, truncation not termination.
5. **The reward.** Passenger weights and the fairness penalty; lambda = {lam:g}, T = {T:g} s from a sweep.
6. **Agents and baselines.** Double DQN from scratch; SB3 DQN and PPO; Webster, actuated, max-pressure, random.
7. **Fixed-time vs RL.** _(Demo: scene Hero, 2 min.)_ Peak wait per person: {f(val(table, 'peak', 'ddqn_fair', 'person_wait'))} s vs {f(val(table, 'peak', 'fixed_matched', 'person_wait'))} s.
8. **The surge.** _(Demo: scene Surge, 1 min.)_ {f(rl_s)} s vs {f(fx_s)} s per person.
9. **The starvation problem.** _(Demo: scene Starvation, 2 min.)_ {meta.get('kpis', [{}, {}])[1].get('detail', '')}.
10. **The bus.** _(Demo: scene Bus, 1 min.)_ {meta.get('kpis', [{}, {}, {}])[2].get('detail', '')}.
11. **Results and the honest finding.** _(Demo: /results and scene Honest, 1 min.)_ {meta.get('honest_finding', '')}
12. **Limits and next steps.** Sim-to-real gap, perfect observations, one junction; corridor control next.

Backups if SUMO GUI lags on the projector: the website served offline (`npx serve web/out`) and `docs/demo.gif`.
"""
    (OUT / "slides.md").write_text(slides, encoding="utf-8")

    viva = f"""# Viva notes

_Answers use this project's own results; numbers filled by `report/fill.py`._

## Write these from memory

Q-learning update:

```
Q(s, a) <- Q(s, a) + alpha * [ r + gamma * max_a' Q(s', a') - Q(s, a) ]
```

One Double DQN training step:

```
a = argmax Q(s) with probability 1 - epsilon, else random
s', r, terminated, truncated = env.step(a)
buffer.add(s, a, r, s', terminated)
batch = buffer.sample(64)
a* = argmax_a' Q_online(s'_b, a')
y  = r_b + gamma * (1 - terminated_b) * Q_target(s'_b, a*)
loss = Huber(Q_online(s_b, a_b), y); backprop; clip gradient norm at 10; Adam step
update the target network from the online network
```

## Likely questions

**Is your state Markov?** No, strictly. It omits upstream arrivals and vehicles between observations, so the agent
acts under partial observability. It works because queues, densities and longest waits summarise most of what
decides the next few seconds.

**Why a target network and a replay buffer?** Bootstrapped targets move with every update and consecutive samples are
correlated; both destabilise Q-learning with function approximation. A slowly changing target and shuffled replay fix
the two problems separately.

**Why does DQN overestimate, and what does Double DQN change?** The max over noisy estimates is biased upward. Double
DQN lets the online network pick the action and the target network evaluate it.

**Why is your reward not simply negative waiting time?** The difference form credits the change an action caused and
is denser. Its discounted return is equivalent to minimising accumulated waiting on the approaches, which is also why
checkpoints are selected with that potential form: the undiscounted sum of differences telescopes to the final state.

**Why can max-pressure match your agent?** It is throughput-optimal under idealised assumptions and needs no training.
Our numbers: {meta.get('honest_finding', '')}

**Would this work on the real junction?** Not as it stands. Sim-to-real gap: sensing errors, driver behaviour,
pedestrians, safety certification. {synthetic}

**How do you know the agent has converged?** By the validation score on held-out seeds across {seeds.get('train', '?')}
training seeds flattening out, not by one training curve. See the learning-curve figure and its seed bands.

**Why are safety constraints in the env, not the reward?** A constraint is a guarantee; a penalty is a price the agent
may choose to pay. `tests/test_safety.py` checks 100 random-policy episodes against the signal states SUMO applied.

**Why is episode end truncation, not termination?** Traffic does not stop at {cfg['sim']['episode_seconds']} s.
Treating the limit as terminal would bias values near the end, so the target bootstraps from the last state.

**Your transitions last 5 s or 13 s. Is constant gamma correct?** It is a semi-MDP simplification. The
`--smdp-discount` flag uses gamma^(dt/5) to test it.

**Why passenger weights of {d['passenger_weights']['bus']:.0f} for a bus?** A stated occupancy assumption. The ablation
runs bus weights of 20, 40 and 60: {ablations[ablations.group == 'bus_weight']['takeaway'].iloc[0] if not ablations.empty and (ablations.group == 'bus_weight').any() else 'pending.'}

**Does the fairness penalty do anything?** {ablations[ablations.group == 'fairness']['takeaway'].iloc[0] if not ablations.empty and (ablations.group == 'fairness').any() else 'Pending.'}

**Why only one junction?** Scope. Corridor multi-agent control is the first extension.
"""
    (OUT / "viva.md").write_text(viva, encoding="utf-8")
    print("report/REPORT.md, report/slides.md, report/viva.md written")

    # README: key results table and hardware line between their markers.
    rows = []
    for key in ORDER:
        if key == "random":
            continue
        cells = [CONTROLLER_LABELS.get(key, key)]
        values = [val(table, r, key, "person_wait") for r in REGIMES]
        if all(v is None for v in values):
            continue
        cells += [f(v) for v in values]
        cells.append(f(val(table, "skewed", key, "max_wait"), 0))
        rows.append(cells)
    block = (
        "Wait per person in seconds (mean over evaluation seeds), and the longest wait in the skewed regime.\n\n"
        + md_table(["Controller", *[f"{r.title()}" for r in REGIMES], "Max wait, skewed (s)"], rows)
        + f"\n\n{meta.get('honest_finding', '')}\n\n"
        + (f"> **Data: synthetic demand.** {synthetic}\n" if meta.get("synthetic_demand") else "")
    )
    plan = load_json(SUMMARY / "training_plan.json", {})
    status = load_json(SUMMARY / "training_status.json", {})
    minutes = sum(j.get("minutes") or 0 for j in status.get("jobs", {}).values())
    hardware = (
        f"This repository's results: profile `{meta.get('profile', '?')}`, {len(status.get('jobs', {}))} training jobs, "
        f"{minutes / 60:.1f} CPU-hours on {plan.get('workers', '?')} workers "
        f"(Intel i5-12450H, 16 GB RAM, Windows 11), measured at {plan.get('speed', {}).get('steps_per_s', 0):.0f} "
        f"decisions per second per simulation."
    )
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    for name, content in (("results", block), ("hardware", hardware)):
        start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
        a, b = readme.index(start) + len(start), readme.index(end)
        readme = readme[:a] + "\n" + content.rstrip() + "\n" + readme[b:]
    readme_path.write_text(readme, encoding="utf-8")
    print("README.md results block updated")


if __name__ == "__main__":
    main()
