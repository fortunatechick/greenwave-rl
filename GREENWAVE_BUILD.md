# GreenWave-RL: One-Day Build Specification

**GreenWave-RL: Fairness-Aware Deep Reinforcement Learning for Adaptive Signal Control under Mixed Indian Traffic**

> This file is the only input needed to build the full project: the simulation, the RL agents, the experiments, the report material, and a portfolio-grade website deployable to Vercel. It is written for **Claude Code** to execute top to bottom in phases, within one working day (about 12–14 hours of wall-clock time, most of it unattended training).

---

## 0. How to use this file (for the human)

1. Create an empty folder `greenwave-rl/`, put this file inside it, and run `git init`.
2. Open Claude Code in that folder and say:
   **"Read GREENWAVE_BUILD.md completely, then execute it phase by phase starting at Phase 0. Follow Section 1 strictly."**
3. Answer the Phase 0 questions (junction, CPU cores, whether you have traffic counts). Everything else has defaults.
4. Leave the machine on during Phase 4, when training runs in the background for several hours.
5. At the end you get a GitHub-ready repo plus a static website in `web/` that you import into Vercel.

**What you must do by hand (Claude Code cannot):** take a photo of the real junction (optional), count vehicles from video (optional; synthetic demand is the default), and click "Import Project" on Vercel (or run `vercel` once logged in).

---

## 1. Operating rules for Claude Code

1. **Read the whole file before writing any code.** Create a task list with one item per phase (Section 12) and tick items off as they finish.
2. **Work in phases, in order.** Each phase has a "Done when" check. Run it. If it passes, commit with `git commit -m "phase N: <summary>"`. Do not move on with a failing check unless you apply the documented fallback.
3. **Never block on long jobs.** Start training and evaluation with `nohup ... > logs/<job>.log 2>&1 &` (or an equivalent background process), record PIDs in `logs/pids.txt`, and poll with `tail`. While training runs, build the website (Phase 5).
4. **Never fabricate results.** Every number shown in the website, README or report must come from files produced by `experiments/export_web.py`. Mock data may exist only in `web/fixtures/` and must be flagged `"mock": true`. The production build must fail if mock data would ship (Section 11.9).
5. **Fallback rule.** If a step fails twice, apply the fallback written for that step, and log the decision in `DECISIONS.md` (date, what failed, what was done instead, effect on results).
6. **Progress log.** Keep `PROGRESS.md` up to date: phase, status, key numbers, and open issues. A returning human should understand the state of the project in 30 seconds.
7. **Ask the human only in Phase 0** (Section 12, Phase 0). After that, use defaults and record choices in `DECISIONS.md`.
8. **Respect the constraint budget.** Use the compute profile chosen in Phase 2 (Section 9). Do not silently cut seeds or steps beyond it; if you must, log it in `DECISIONS.md` and show it on the website's Results page (`meta.json → deviations`).
9. **Code quality.** Python 3.11, type hints, `ruff` clean, `pytest` green. TypeScript strict, `eslint` clean. All randomness is seeded. One command regenerates every result: `make all`.
10. **Platform notes.** Works on Linux, macOS and Windows. On Windows, prefer WSL2 for parallel training. Every multiprocessing entry point must sit under `if __name__ == "__main__":`.

---

## 2. The project

### 2.1 Abstract

Fixed-time traffic signals cannot respond to demand that changes by the minute. This project builds a microscopic simulation of a real signalised junction, populated with mixed traffic (two-wheelers, auto-rickshaws, cars, buses), and trains deep reinforcement learning agents to choose signal phases from live queue observations. We compare Double DQN, DQN and PPO against fixed-time, actuated and max-pressure controllers across four demand regimes. We contribute a passenger-weighted reward with a fairness penalty that prevents the agent from starving low-volume approaches, and we measure how well policies trained on one demand pattern survive on another, with and without domain randomisation.

### 2.2 Problem statement

Given a signalised junction with time-varying, heterogeneous traffic, learn a phase-selection policy that minimises delay per person, keeps the worst-case wait bounded, and stays effective when demand shifts away from what it was trained on.

### 2.3 Motivation

- Signal timing plans are tuned by hand for an average hour and go stale.
- Indian traffic is mixed and weakly lane-disciplined, which most published RL signal work ignores.
- Counting vehicles equally undervalues a bus carrying 40–50 people against a car carrying one or two.
- RL agents that minimise average delay can learn to hold a minor road on red indefinitely. A deployable controller must not.

### 2.4 Objectives

1. Build a SUMO model of one real junction with four vehicle classes and sub-lane (lateral) movement.
2. Formulate signal control as a Markov decision process and implement a Gymnasium environment with environment-enforced safety constraints.
3. Train Double DQN (from scratch), DQN and PPO (Stable-Baselines3), and implement four classical baselines.
4. Design and test a passenger-weighted, fairness-aware reward.
5. Quantify generalisation across demand regimes and the effect of domain randomisation.
6. Deliver a side-by-side demo: locally in SUMO GUI, and publicly on a website that replays recorded simulations.

### 2.5 Novelty (the three choices that separate this from a tutorial)

- **Reward design:** passenger-weighted delay plus a maximum-wait fairness penalty. This is the original contribution.
- **Setting:** real junction geometry, left-hand traffic, four mixed vehicle classes with sub-lane movement, approach-wise split phasing as used at Indian junctions. Not a synthetic four-way grid.
- **Honest generalisation study:** train on one regime, test on the others, report failures, and measure what domain randomisation recovers.

RL for traffic signals is a well-published field. The novelty is in these three choices, not the idea. **Do not drop more than one of them under any time pressure.**

---

## 3. Locked technical decisions

| Area | Decision |
| --- | --- |
| Python | 3.11, virtualenv in `.venv/`, dependencies pinned in `requirements.txt` |
| Simulator | SUMO via `pip install eclipse-sumo traci libsumo sumolib` (sets up binaries; `SUMO_HOME` from `python -c "import sumo; print(sumo.SUMO_HOME)"`) |
| Sim API | `libsumo` for headless training (fast, one simulation per process); `traci` with connection labels for GUI demo and multi-sim processes. Switch with env var `LIBSUMO_AS_TRACI=1` |
| RL environment | Gymnasium API (`terminated` / `truncated` separated). `sumo-rl` used as a reference only; own wrapper |
| Main agent | **Double DQN written from scratch in PyTorch** (`agents/dqn_scratch.py`) |
| Comparison agents | Stable-Baselines3 `DQN` (vanilla DQN, not Double DQN; state this in the report) and `PPO` |
| Tracking | TensorBoard (default); Weights & Biases optional via flag |
| Analysis | pandas, numpy, scipy (Welch t-tests), matplotlib, seaborn |
| Local demo | `sumo-gui` × 2 via TraCI + Streamlit live plots |
| Website | Next.js (App Router, TypeScript, static export) + Tailwind CSS + shadcn/ui + Motion + Recharts + KaTeX, deployed on Vercel |
| Phasing | Approach-wise split phasing: 4 phases, one per approach, each serving all movements of that approach. Free left turn configurable (`free_left: true` default, common in Mumbai) |
| Traffic side | Left-hand traffic (`netconvert --lefthand`) |
| Step length | 1.0 s simulation step |
| Decision interval | Δ = 5 s (ablation: 10 s, 15 s) |

---

## 4. The decision process (MDP) — exact specification

### 4.1 Elements

| Element | Definition |
| --- | --- |
| State | Per incoming lane: queue (PCU-weighted halting count) and density (PCU on lane / lane capacity), normalised to [0, 1.5]. Plus current phase (one-hot, 4), time since last change normalised by max green, and longest current accumulated wait per approach normalised by T (4 values). |
| Action | Index of the next green phase (approach). Choosing the current phase extends it by Δ. |
| Safety constraints | Minimum green 10 s, yellow 3 s on every change, optional all-red 0 s (configurable), maximum green 60 s. **Enforced by the environment, never learned.** |
| Reward (baseline) | Reduction in total accumulated waiting time on incoming lanes since the last decision. |
| Reward (ours) | Passenger-weighted waiting-time reduction, minus a penalty when any approach's longest wait exceeds threshold T. |
| Episode | 3,600 simulated seconds. Discount γ = 0.99 per decision. Episode end is **truncation**, not termination: bootstrap from the last state. |

Lane capacity in PCU = lane length / 7.5 m. PCU factors (IRC:106-1990 style assumptions, state them in the report): two-wheeler 0.5, car 1.0, auto-rickshaw 1.2, bus 2.2.

### 4.2 Timing state machine (in `env/signal_env.py`)

```
GREEN(p) --agent picks p--> GREEN(p) for Δ more seconds
GREEN(p) --agent picks q≠p--> YELLOW(p) 3 s --> [ALL_RED t_ar] --> GREEN(q) for at least min_green
```

- The agent is **only queried at legal decision points**: when the current green has run at least `min_green`. Between a switch and the next decision, the environment steps SUMO internally (3 s yellow + 10 s min green = 13 s).
- If the current green reaches `max_green` (60 s), the environment **forces** a switch to the approach with the longest current wait (ties: next in cycle order) without querying the agent. Count forced switches as a logged metric.
- Reward for a decision covers all simulated seconds until the next decision point (including yellow).
- Transitions have variable duration (5 s or 13 s). We use a constant γ per decision (semi-MDP simplification); note it in the report and viva notes. Optional flag `--smdp-discount` uses γ^(Δt/5).
- Green durations reachable: 10, 15, …, 60 s.

### 4.3 Reward formulas

Baseline:

```latex
r_t^{\text{wait}} = \frac{1}{\kappa}\big(W_{t-1} - W_t\big)
```

Ours, where `w_c` is the passenger weight of class c, `W_{c,t}` the summed accumulated wait of class-c vehicles on incoming lanes, and `T` the fairness threshold:

```latex
r_t = \frac{1}{\kappa}\sum_{c} w_c \,\big(W_{c,t-1} - W_{c,t}\big) \;-\; \lambda \,\frac{\max\!\big(0,\; \max_{a \in \text{approaches}} \text{wait}_a - T\big)}{T}
```

Defaults: κ = 100, λ = 1.0, T = 90 s. Passenger weights: two-wheeler 1.5, car 2, auto-rickshaw 2.5, bus 40 (assumptions; sensitivity tested with bus ∈ {20, 40, 60}).

Other rewards for ablations (all in `env/rewards.py`, same interface `reward(prev_obs_info, obs_info) -> float`):
- `queue`: −(total halting PCU) / κ_q
- `pressure`: −|Σ incoming queue − Σ outgoing queue| / κ_q
- `passenger_nofair`: ours with λ = 0
- `vehicle_fair`: ours with all w_c = 1

Accumulated waiting time comes from `traci.vehicle.getAccumulatedWaitingTime`. **Set `--waiting-time-memory 3600`**, otherwise SUMO forgets waits older than 100 s and the fairness term breaks.

Quick tuning (in the day profile, skewed regime, short runs): λ ∈ {0.25, 1, 4} × T ∈ {60, 90, 120}. Pick the setting with the lowest person-delay subject to max wait ≤ 1.2·T. Record the choice in `DECISIONS.md`.

### 4.4 DQN objective (for the report and method page)

```latex
L(\theta) = \mathbb{E}\Big[\big(r + \gamma \max_{a'} Q_{\theta^-}(s', a') - Q_\theta(s, a)\big)^2\Big]
```

Double DQN target (what the scratch agent implements):

```latex
y = r + \gamma \,(1 - d)\; Q_{\theta^-}\!\big(s', \arg\max_{a'} Q_\theta(s', a')\big)
```

with `d = 1` only on true termination (never on time-limit truncation). Use Huber loss and gradient-norm clipping at 10.

---

## 5. Simulation specification

### 5.1 Network (`network/`)

Configured in `configs/junction.yaml`:

```yaml
name: "<JUNCTION NAME>"          # asked in Phase 0
bbox: [west, south, east, north] # optional; enables OSM import
approaches: [N, E, S, W]          # cycle order
lanes_in: {N: 2, E: 3, S: 2, W: 3}
lanes_out: {N: 2, E: 3, S: 2, W: 3}
approach_length_m: 250
lane_width_m: 3.5
free_left: true
```

Two build paths in `network/build_network.py`:

- **Path A (OSM, if bbox given):**
  `python $SUMO_HOME/tools/osmGet.py --bbox W,S,E,N -p network/osm/junction` then
  `netconvert --osm-files network/osm/junction_bbox.osm.xml --lefthand --geometry.remove --junctions.join --tls.guess-signals --tls.discard-simple --tls.join --remove-edges.isolated --keep-edges.by-vclass passenger --output.street-names -o network/junction_osm.net.xml`.
  Then crop to the target junction and its four approaches, and overwrite the TLS program with the 4-phase split program.
- **Path B (plain XML, default and fallback):** generate `.nod.xml`, `.edg.xml`, `.con.xml`, `.tll.xml` from `junction.yaml` and run `netconvert --lefthand` on them. Geometry and lane counts mirror the real junction as described by the user.

**Timebox: 60 minutes for Path A.** If OSM lanes or phases are wrong after that, switch to Path B and log it. Path B is fully acceptable for the report ("geometry simplified by hand to the observed lane counts").

Output: `network/junction.net.xml` with TLS id `J0` and exactly 4 green phases (one per approach), each followed by its yellow phase.

### 5.2 Vehicle types (`demand/vtypes.add.xml`)

| Class | SUMO vClass | Length × width (m) | Max speed (m/s) | Sub-lane settings |
| --- | --- | --- | --- | --- |
| two_wheeler | motorcycle | 1.9 × 0.8 | 16 | `latAlignment="arbitrary"`, `minGapLat="0.25"`, `lcSublane="2"` |
| auto_rickshaw | passenger (custom type) | 2.6 × 1.4 | 12 | `latAlignment="arbitrary"`, `minGapLat="0.3"` |
| car | passenger | 4.3 × 1.8 | 16 | `minGapLat="0.4"` |
| bus | bus | 12.0 × 2.5 | 13 | `latAlignment="center"` |

Enable the sub-lane model with `--lateral-resolution 0.8`. The ablation "sub-lane off" removes that flag and sets `latAlignment` defaults.

Emissions: `--device.emissions.probability 1` with default HBEFA classes per type (state assumption).

### 5.3 Demand (`demand/generate.py`)

- Input: `demand/counts.csv` with columns `approach,turn,class,veh_per_hour,period` where period ∈ {peak, offpeak}.
- **Default (no field counts):** generate synthetic counts and set `meta.synthetic_demand = true`. The website and report must say so.
  - Class mix by vehicle count: two-wheeler 45 %, car 30 %, auto-rickshaw 18 %, bus 7 %.
  - Turn split: left 25 %, through 55 %, right 20 %.
  - Peak volume per approach chosen so the Webster plan gives a degree of saturation ≈ 0.85 (major approaches 1.5× minor).
- If the human supplies counts from 15-minute videos, scale ×4 to hourly flows.
- Arrivals are Poisson: SUMO `<flow ... period="exp(rate)">` per (origin, destination, class).

Regimes (route files in `demand/routes/<regime>.rou.xml`):

| Regime | Definition |
| --- | --- |
| low | 0.4 × peak on all approaches |
| peak | 1.0 × peak |
| skewed | one major approach 1.6 × peak, others 0.6 × peak |
| surge | 0.7 × peak baseline, plus a 10-minute burst (t = 1500–2100 s) at 2.5 × on one approach |

Domain randomisation: pre-generate a pool of 200 route files in `demand/dr_pool/` where each approach's flow is scaled by an independent U(0.5, 1.5) factor (base: peak). Sample one per training episode.

### 5.4 SUMO command-line flags (single source of truth: `greenwave/sumo_utils.py`)

```
--step-length 1 --seed <seed> --no-step-log --no-warnings
--waiting-time-memory 3600 --time-to-teleport 300
--lateral-resolution 0.8
--tripinfo-output <path> --tripinfo-output.write-unfinished
--device.emissions.probability 1
--collision.action warn
```

Log teleports and collisions per episode. If teleports exceed 1 % of vehicles in any baseline run, fix geometry or demand before training (it means gridlock artefacts).

Seeds: training seeds 0–999 (random per episode), evaluation seeds 1000–1009 (never used in training), replay seed 1000.

---

## 6. Baseline controllers (`controllers/`)

All controllers implement the same interface as the agent (`act(obs, info) -> action`), run through the same environment with the same safety constraints, and are evaluated by identical code.

1. **Fixed-time (Webster).** Cycle length

   ```latex
   C_0 = \frac{1.5\,L + 5}{1 - Y}, \qquad Y = \sum_i y_i,\quad y_i = \frac{q_i}{s_i}
   ```

   L = lost time per cycle (n_phases × (yellow + all-red + 2 s start-up loss)), q_i the critical flow of approach i in PCU/h, s_i its saturation flow (IRC-style 525·W PCU/h for approach width W in m; state the assumption). Clamp C_0 to [40, 150] s. Effective green split proportional to y_i, each green clamped to [min_green, max_green]. Two variants:
   - `fixed_matched`: Webster plan computed for each regime (strongest fixed-time).
   - `fixed_peak`: the peak plan applied to every regime (the realistic, stale plan).
2. **Actuated.** SUMO's built-in `type="actuated"` program with minDur 10, maxDur 60, default `max-gap` 3 s.
3. **Max-pressure.** At each decision point, serve the phase with the largest pressure, where a phase's pressure = Σ over its movements (halting PCU on incoming lane − halting PCU on outgoing lane). Same min/max green and Δ as the agent.
4. **Random phase.** Uniform over phases, same constraints. Sanity floor.

Unit tests: Webster on a hand-worked example; max-pressure picks the right phase on a constructed queue state; actuated loads without error.

---

## 7. Agents

### 7.1 Double DQN from scratch (`agents/dqn_scratch.py`) — main agent

- MLP: input → 128 → 128 → 4, ReLU.
- Replay buffer 50k, batch 64, Adam lr 1e-4, hard target update every 500 steps, learning starts after 2,000 steps, train every step.
- ε-greedy linear decay 1.0 → 0.05 over the first 50 % of training steps.
- Huber loss, grad-norm clip 10, observation already normalised by the env.
- Evaluate every 10k steps on 2 held-out validation seeds (900, 901, not eval seeds); checkpoint the best by mean eval reward.
- Must pass a **toy sanity test** first: on `network/toy/` (symmetric 4-way, 1 lane per approach, strongly unbalanced demand) it must beat random within 20k steps.

Training-step pseudocode (also goes in `report/viva.md`, to rehearse on a whiteboard):

```
a = argmax Q(s) w.p. 1-ε else random
s', r, terminated, truncated = env.step(a)
buffer.add(s, a, r, s', terminated)
batch = buffer.sample(64)
a* = argmax_a' Q_online(s'_b, a')
y = r_b + γ (1 - terminated_b) Q_target(s'_b, a*)
loss = Huber(Q_online(s_b, a_b), y); step Adam; clip grads
every 500 steps: θ⁻ ← θ
```

### 7.2 Stable-Baselines3 (`agents/train_sb3.py`)

- `DQN`: `policy_kwargs=dict(net_arch=[128,128])`, buffer 50k, batch 64, lr 1e-4, `target_update_interval=500`, `exploration_fraction=0.5`, `exploration_final_eps=0.05`, `learning_starts=2000`.
- `PPO`: `SubprocVecEnv` with 4 envs (one libsumo sim per process), `n_steps=512`, `batch_size=64`, `n_epochs=10`, lr 3e-4, γ 0.99, GAE λ 0.95, clip 0.2, `ent_coef=0.01`, net_arch [128,128].
- Both use the identical environment and reward.

### 7.3 Stretch goal (only if time remains after Phase 8)

Independent DQN per junction on a 2–3 junction corridor (`network/corridor/`). Not required for completion.

---

## 8. Evaluation specification

### 8.1 Testing pipeline

1. Freeze the policy; ε = 0 (PPO: deterministic action).
2. Run 10 evaluation seeds (1000–1009) per regime per controller.
3. Export tripinfo for every vehicle, plus per-step env logs (queues, phase, max wait).
4. Compute metrics per class and per approach; report mean ± standard deviation over seeds, and Welch's t-test against `fixed_matched` and against `max_pressure` (mark p < 0.05).

### 8.2 Metrics (`greenwave/metrics.py`)

| Metric | Unit | Exact definition |
| --- | --- | --- |
| Avg waiting time per vehicle | s | Mean tripinfo `waitingTime` (includes unfinished vehicles) |
| Avg waiting time per person | s | Σ w_c·wait / Σ w_c over vehicles |
| Avg queue length | vehicles | Mean over seconds of total halting vehicles on incoming lanes |
| Throughput | veh/h | Arrived vehicles per simulated hour |
| Max wait on any approach | s | Max `waitingTime` over vehicles, per approach; report the max over approaches |
| Wait p95 | s | 95th percentile per-vehicle wait (fairness distribution) |
| Delay by vehicle class | s | Mean `timeLoss` per class |
| CO2 | g / vehicle | Mean `CO2_abs` from the emissions device / 1000 |
| Forced switches, teleports | count | Diagnostics |

### 8.3 Comparison experiments

1. **Main table:** every controller in every regime, all metrics, mean ± std over 10 seeds. RL rows: regime-matched Double DQN (fair reward), DR Double DQN (fair reward), SB3 DQN, PPO.
2. **DQN vs PPO vs Double DQN:** final performance, learning curves (mean ± std band over training seeds), seed variance.
3. **Generalisation matrix:** train on regime A, test on regime B, all pairs. 4 × 4 grid of person-weighted waiting time (and a second grid of max wait).
4. **Domain randomisation:** the DR agent tested on all 4 regimes, shown as a fifth row alongside the matrix, plus a "gap recovered" percentage: (off-diagonal mean − DR) / (off-diagonal mean − diagonal).
5. **Fairness:** distribution (ECDF and box plot) of per-vehicle waits for each reward design.

### 8.4 Ablation study (on the peak regime unless stated)

| Change | Question answered |
| --- | --- |
| Reward: waiting vs queue vs pressure vs ours | Which objective produces the best real behaviour? |
| Remove fairness penalty (λ = 0), skewed regime | Does the agent starve the minor road? |
| Vehicle-count vs passenger weighting | Do buses clear faster, and at what cost to others? |
| Bus weight 20 / 40 / 60 | Sensitivity of results to the occupancy assumption |
| State without phase timer; without max-wait feature | Which observations matter? |
| Decision interval 5 s vs 10 s vs 15 s | Reactivity against stability |
| Sub-lane model off | Does modelling mixed traffic change the ranking of controllers? (re-run baselines too) |

---

## 9. Compute profiles and the budget planner

The original plan assumed 10 weeks, 200k–300k steps and 5 seeds per configuration. For a one-day build, Claude Code measures speed first and picks a profile. **All three profiles are implemented**; only the chosen one is run today.

| Profile | Main runs | Ablation runs | Seeds (main / ablation) | Purpose |
| --- | --- | --- | --- | --- |
| quick | 20k steps | 10k | 1 / 1 | CI and smoke tests only |
| day (target) | 100k steps | 50k | 3 / 2 | One-day build |
| full | 250k steps | 150k | 5 / 3 | The original blueprint; run later for the final report |

`experiments/budget.py`:
1. Runs 2 headless episodes of the peak regime with a random policy; measures environment steps per second.
2. Estimates training cost (env time + ~1.5 ms per gradient step) for every job in `configs/experiments.yaml` under each profile.
3. Given `--hours` (default 7) and `--workers` (default: physical cores − 1), schedules jobs longest-first and picks the largest profile that fits. If even `day` does not fit, scale step counts down uniformly (never below 60k for main runs) and log the deviation.
4. Writes `runs/plan.json` used by the job queue.

Job list for the day profile (≈ 40 jobs):
- Double DQN fair × 4 regimes × 3 seeds (generalisation, diagonal of main table)
- Double DQN fair + DR × 3 seeds
- SB3 DQN × 3, PPO × 3 (peak)
- Reward ablations: waiting, queue, pressure, passenger_nofair (skewed), vehicle_fair × 2 seeds
- Bus weight 20 and 60 × 2 seeds
- State ablations × 2 variants × 2 seeds
- Decision interval 10 s and 15 s × 2 seeds
- Sub-lane off × 2 seeds
- λ/T sweep: 9 short runs (30k steps, 1 seed), run first

Training is CPU-bound; a GPU adds almost nothing. Laptop with 8–16 GB RAM is enough.

`experiments/run_queue.py`: ProcessPoolExecutor, resumable (skips jobs with `runs/<job>/done.flag`), per-job TensorBoard logs, a `status.json` summary, and a one-line progress print per finished job.

---

## 10. Repository layout

```
greenwave-rl/
  README.md  LICENSE (MIT)  .gitignore  Makefile  requirements.txt  pyproject.toml
  GREENWAVE_BUILD.md  PROGRESS.md  DECISIONS.md
  configs/
    junction.yaml  sim.yaml  demand.yaml  rewards.yaml  train.yaml  experiments.yaml
    profiles/quick.yaml  profiles/day.yaml  profiles/full.yaml
  network/
    build_network.py  plain/  osm/  toy/  junction.net.xml  tls_fixed_<regime>.add.xml
  demand/
    vtypes.add.xml  counts.csv  generate.py  routes/  dr_pool/
  greenwave/                  # importable package
    sumo_utils.py  metrics.py
    env/signal_env.py  env/state.py  env/rewards.py
    controllers/fixed_time.py  controllers/actuated.py  controllers/max_pressure.py  controllers/random_phase.py
    agents/dqn_scratch.py  agents/train_sb3.py
  experiments/
    budget.py  run_queue.py  evaluate.py  generalisation.py  ablations.py
    figures.py  record_replay.py  export_web.py  make_readme_gif.py
  demo/
    side_by_side.py  dashboard.py
  tests/
    test_safety.py  test_rewards.py  test_webster.py  test_max_pressure.py
    test_metrics.py  test_export_schema.py  test_env_smoke.py
  runs/  results/  logs/        # gitignored except results/summary/
  report/
    REPORT.md  slides.md  viva.md  figures/
  docs/  demo.gif  og.png
  web/                          # Next.js site (Section 11)
  .github/workflows/ci.yml
```

`.gitignore`: `.venv/`, `runs/`, `logs/`, `results/raw/`, `*.pt` except `results/models/best_*.pt` (keep best checkpoints if < 5 MB each), `web/node_modules/`, `web/.next/`, `web/out/`, `demand/dr_pool/`.

`Makefile` targets: `setup network demand toy baselines bench train eval figures replays export web-dev web-build demo test all`.

---

## 11. Website specification (Vercel)

### 11.1 Architecture

SUMO cannot run on Vercel. The site is a **static Next.js export** that plays back **recorded simulations** and renders **exported results**. Everything the site shows is produced by `experiments/export_web.py` into `web/public/data/`.

```
Python (local)                         Web (static, Vercel)
runs/ + results/ ──export_web.py──▶ web/public/data/*.json ──▶ pages read at build time
record_replay.py ─────────────────▶ web/public/data/replays/*.json ──▶ fetched on demand
```

- `next.config.ts`: `output: "export"`, `images: { unoptimized: true }`, `trailingSlash: true`.
- Results JSON is imported at build time (static). Replays are fetched lazily on the client.
- No server, no API routes, no secrets. Zero running cost.

### 11.2 Data contract (validated on both sides)

Python validates with `pydantic` before writing; the site validates with `zod` at build time. Shared field names, snake_case.

`meta.json`
```json
{ "mock": false, "profile": "day", "generated_at": "ISO-8601", "git_sha": "abc123",
  "synthetic_demand": true, "junction_name": "...", "network_source": "osm|plain",
  "sumo_version": "...", "seeds": {"train": 3, "eval": 10},
  "deviations": ["string, from DECISIONS.md"],
  "headline": {"regime": "surge", "metric": "person_wait",
               "rl": 0.0, "fixed": 0.0, "max_pressure": 0.0} }
```

`network.json`
```json
{ "bounds": [xmin, ymin, xmax, ymax],
  "lanes": [{"id": "N_in_0", "approach": "N", "dir": "in", "width": 3.5, "shape": [[x, y], ...]}],
  "junction_shape": [[x, y], ...],
  "signals": [{"approach": "N", "pos": [x, y], "angle": 0}] }
```

`results/main.json`: `[{regime, controller, metric, mean, std, n, p_vs_fixed, p_vs_mp}]`
`results/curves.json`: `{agent: {steps: [...], mean: [...], std: [...]}}`
`results/generalisation.json`: `{metric, regimes: [...], matrix: [[mean...]], std: [[...]], dr_row: [...], gap_recovered_pct}`
`results/fairness.json`: `{reward_design: {ecdf_x: [...], ecdf_y: [...], p50, p95, max}}`
`results/per_class.json`: `[{regime, controller, class, delay_mean, delay_std}]`
`results/ablations.json`: `[{group, variant, metric, mean, std, n}]`

`replays/<scene>.json` (compact, target < 2 MB each, served gzip by Vercel)
```json
{ "scene": "surge", "title": "...", "caption": "...",
  "left":  {"controller": "fixed_matched", "label": "Fixed-time (Webster)"},
  "right": {"controller": "ddqn_fair_dr", "label": "GreenWave (ours)"},
  "regime": "surge", "seed": 1000, "t0": 1400, "t1": 2200, "dt": 1,
  "classes": ["two_wheeler", "auto_rickshaw", "car", "bus"],
  "events": [{"t": 1500, "label": "Surge starts on E"}],
  "sides": {
    "left":  {"veh_class": [0, 2, ...],
              "frames": [[vehIdx, x10, y10, angleDeg, vehIdx, ...], ...],
              "signal": ["GrrrGrrr...", ...], "phase": [0, 0, ...],
              "series": {"wait_now": [...], "queue_by_approach": [[n,e,s,w], ...],
                         "person_wait_cum": [...], "max_wait": [...]}},
    "right": { "...same shape..." } } }
```
Positions are SUMO metres × 10 as integers; one frame per second; the renderer interpolates.

Scenes to record (`experiments/record_replay.py`, same seed on both sides, using TraCI subscriptions for speed):

| Scene | Regime | Left | Right | Window (s) |
| --- | --- | --- | --- | --- |
| hero | peak | fixed_peak | ddqn_fair (peak) | 600–1200 |
| surge | surge | fixed_matched | ddqn_fair_dr | 1400–2200 |
| starvation | skewed | ddqn_passenger_nofair | ddqn_fair | 600–1400 |
| bus | peak | ddqn_vehicle_fair | ddqn_fair | 600–1200 |
| honest | peak | max_pressure | ddqn_fair | 600–1200 |
| generalisation | surge | ddqn_fair trained on low | ddqn_fair_dr | 1400–2200 |

### 11.3 Design direction: "Control room at night"

A calm, precise, dark-first interface that feels like a traffic management centre. Signal colours are used **only** for meaning (signal state, good/bad), never decoration.

Design tokens (CSS variables on `:root`, light theme overrides under `[data-theme="light"]` and `prefers-color-scheme`):

| Token | Dark | Light | Use |
| --- | --- | --- | --- |
| `--bg` | `#0A0C0F` | `#F6F7F9` | page (asphalt) |
| `--surface-1` | `#111419` | `#FFFFFF` | cards |
| `--surface-2` | `#181C22` | `#EEF0F3` | raised, inputs |
| `--line` | `#252A32` | `#DADDE3` | borders, grid |
| `--text` | `#E8EAED` | `#0F1216` | body |
| `--muted` | `#8A93A0` | `#5B6370` | secondary |
| `--go` | `#3DDC84` | `#119C55` | green signal, improvement |
| `--amber` | `#FFB020` | `#B87500` | yellow signal, warning |
| `--stop` | `#FF4D4F` | `#D42A2C` | red signal, regression |
| `--wave` | gradient `#3DDC84 → #2BD4C8` | same, darker | brand accent, ours |
| `--veh-2w` | `#7DD3FC` | `#0284C7` | two-wheeler |
| `--veh-auto` | `#FDE047` | `#A16207` | auto-rickshaw |
| `--veh-car` | `#CBD5E1` | `#475569` | car |
| `--veh-bus` | `#C4B5FD` | `#6D28D9` | bus |

Vehicle classes are also distinguished by **shape and size** (two-wheeler: thin capsule; auto: rounded small rectangle; car: rectangle; bus: long rectangle), so colour is never the only cue.

Typography: **Geist Sans** (UI and body), **Geist Mono** (all numbers, timers, tables, tabular-nums), **Instrument Serif** italic for at most 3–4 display words (e.g., hero "*learned*"). Fluid type scale with `clamp()`; hero 56–88 px.

Texture: a faint 24 px blueprint grid on the background, a subtle noise overlay at 3 % opacity, 1 px borders, 14 px radii, no heavy drop shadows (use inner glow on focused cards).

Logo: wordmark "GreenWave" with a 3-dot vertical signal glyph whose bottom dot is `--go`. Favicon: the glyph alone (SVG + 32 px PNG).

Motion (Motion library): scroll-reveal fade-up 12 px over 400 ms, number counters on first view, phase-change pulse on signal heads. **All motion is disabled under `prefers-reduced-motion`.**

### 11.4 Pages

**`/` Home**
1. **Hero.** Full-bleed canvas playing the `hero` replay in a loop behind a dark gradient scrim (only the right side, our agent). Headline: "Signal timing, *learned*." Sub-headline: one sentence from the abstract. Three KPI tiles from `meta.headline` and `main.json` (person-wait reduction vs fixed-time in surge, max-wait reduction vs no-fairness agent, bus delay change), with counters. CTAs: "Watch the duel" → `/demo`, "Read the method" → `/method`. If a number is missing, the tile shows "pending" (never a placeholder number).
2. **The problem.** Four cards for the four motivation points, each with a small inline SVG icon.
3. **How it works.** Animated pipeline diagram (SVG) of the 8 system stages: network builder → demand generator → SUMO → Gym env → agent → baselines → evaluator → demo. Hover shows a one-line description.
4. **Three contributions.** Reward design (with the formula rendered by KaTeX), real mixed-traffic setting, honest generalisation.
5. **Results at a glance.** Mini generalisation heatmap + main bar chart (surge regime) linking to `/results`.
6. **The honest finding.** A callout that states where RL beats and where it loses to max-pressure, generated from data.
7. **Footer.** GitHub link, course credit line, "Data: synthetic demand" badge if applicable, build SHA and date.

**`/demo` The Arena (the centrepiece)**
- Two synchronised canvases side by side (stacked on mobile) with labels "Left" / "Right" and controller names.
- Scene picker as pill tabs: Hero, Surge, Starvation, Bus, Honest, Generalisation. Each scene shows its title and one-line caption explaining what to look at.
- Transport bar: play/pause, speed 1× / 4× / 16×, scrubber with event markers (e.g., surge start), current sim time in mono.
- Under the canvases: live-synced Recharts line chart of `wait_now` for both sides, and per-approach queue bars (N/E/S/W) for both sides, updating with the playhead.
- HUD overlay per canvas: phase name, time in phase, current max wait (turns amber above T, red above 1.5·T).
- Legend for vehicle classes (shape + colour). Toggle "highlight buses" (dims other classes) for the Bus scene.
- Keyboard: Space play/pause, ←/→ ±10 s, 1/2/3 speeds, `B` bus highlight. Visible shortcut hint.

**`/results`**
- Regime selector (tabs) + metric selector.
- Main table: controllers as rows, metrics as columns, mean ± std, best value per column bold, `--go`/`--stop` arrows vs fixed-time, significance dot for p < 0.05. Sortable. Mobile: horizontal scroll inside the card only.
- Learning curves: Double DQN vs SB3 DQN vs PPO with std bands.
- Generalisation: two custom SVG heatmaps (without DR, with DR row), diverging colour scale centred on the diagonal mean, value labels in cells, "gap recovered" stat.
- Fairness: ECDF of per-vehicle wait for each reward design with T marked; p95 and max called out.
- Per-class delay: grouped bars per controller.
- Ablations: compact table grouped by question with a one-line takeaway per group (takeaway text written into `ablations.json` by the export script from the numbers, using fixed templates, not free invention).
- CO2 per vehicle bar chart.
- "Deviations from the full protocol" box listing `meta.deviations` and the profile used.

**`/method`**
- MDP table (state, action, constraints, reward, episode), timing state machine diagram (SVG), reward formulas and DQN/Double DQN formulas (KaTeX, rendered at build time), algorithm table, baselines with the Webster formula, training pipeline, evaluation protocol, data strategy and passenger-weight assumptions.

**`/junction`**
- The real junction: photo (`web/public/site.jpg` if provided, else a tasteful placeholder card saying "site photo not added") beside the rendered network.
- Network facts (lanes per approach, phases, free left), demand table per regime and class, PCU and passenger weights, a "synthetic demand" notice when true.

**`/about`**
- Project credits (course: Artificial Intelligence, B.Tech Computer Engineering, 3rd year), tech stack, limitations (sim-to-real gap, perfect observations, semi-MDP simplification), future extensions, reading list, and a short viva-style FAQ (7 questions from Section 16).

### 11.5 Replay engine (`web/lib/replay/`)

- Canvas 2D, sized to container with `devicePixelRatio` scaling, ResizeObserver.
- Static road layer (lanes, markings, stop lines, junction polygon) pre-rendered once to an offscreen canvas per size; per frame only vehicles and signal heads are drawn.
- World → screen transform fitted to `network.bounds` with padding; y-axis flipped.
- Linear interpolation of position between 1 s frames; angle interpolated along the shortest arc. Vehicles that appear or disappear fade over 300 ms.
- One shared clock (zustand store) drives both canvases and the charts, so they are always in sync. `requestAnimationFrame` loop pauses when the tab is hidden or the canvas is off-screen (IntersectionObserver).
- Signal heads: three-dot glyph at each stop line, active dot coloured from the SUMO state string for that approach.
- Optional queue heat: tint each incoming lane by its queue normalised to capacity.
- Target 60 fps with 400 vehicles per side on a mid-range laptop. Hero canvas on mobile renders at 30 fps.

### 11.6 Components

`SiteHeader` (sticky, translucent with backdrop blur, active link indicator), `ThemeToggle`, `KpiTile`, `SectionHeading`, `PipelineDiagram`, `FormulaBlock` (KaTeX), `ReplayCanvas`, `ArenaControls`, `Scrubber`, `ScenePicker`, `ClassLegend`, `ResultsTable`, `Heatmap`, `EcdfChart`, `CurveChart`, `Callout`, `Badge`, `SiteFooter`. Use shadcn/ui for Tabs, Select, Slider, Tooltip, Switch; restyle to the tokens.

### 11.7 Quality bars

- Lighthouse (mobile) on `/`: Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95, SEO ≥ 95.
- First-load JS for `/` ≤ 200 KB gzip. Recharts and the arena code are lazy-loaded.
- WCAG AA contrast for all text; visible focus rings; all controls keyboard-operable; canvases have `aria-label` and a text summary below them.
- Responsive from 360 px to 1920 px. No horizontal page scroll at 360 px.
- No layout shift from fonts (`next/font`), no console errors.

### 11.8 SEO and sharing

`metadata` per page (title, description), `sitemap.xml` and `robots.txt` generated at build, Open Graph and Twitter card using `public/og.png` (1200 × 630, generated by `web/scripts/make-og.mjs` with `sharp` from an SVG template that includes the headline KPI), canonical URL from env `NEXT_PUBLIC_SITE_URL`.

### 11.9 Honesty guards (must implement)

- `web/scripts/check-data.mjs` runs before `next build`: validates every JSON against the zod schemas and **exits non-zero if `meta.mock === true` and `VERCEL_ENV === "production"`** or if `CI_REQUIRE_REAL_DATA=1`.
- During development, if `meta.mock` is true, show a visible amber "Preview data — not real results" banner on every page.

### 11.10 Website tech setup

```
cd web
npx create-next-app@latest . --ts --tailwind --eslint --app --src-dir --import-alias "@/*"
npx shadcn@latest init
npm i motion recharts zustand zod katex geist
npm i -D sharp
```
`package.json` scripts: `dev`, `prebuild: node scripts/check-data.mjs`, `build`, `lint`, `typecheck: tsc --noEmit`.

---

## 12. Phase plan (one day)

Times are offsets from the start. Phases 4 and 5 run in parallel.

### Phase 0 — Setup and toy junction (0:00–0:40)

Ask the human, in one message:
1. Which junction? Name, and either a bounding box (W,S,E,N) or "use plain XML". Lane counts per approach if known. Default: a plain-XML 4-arm junction, 3 lanes on the major road, 2 on the minor road.
2. CPU cores and RAM, and OS. Default: detect automatically.
3. Do you have vehicle counts? Default: no (synthetic demand).

Then:
- Create the repo layout (Section 10), `.venv`, `requirements.txt` (gymnasium, stable-baselines3, sb3-contrib, torch (CPU), eclipse-sumo, traci, libsumo, sumolib, numpy, pandas, scipy, matplotlib, seaborn, pydantic, pyyaml, tensorboard, streamlit, pytest, ruff, pillow, tqdm), `Makefile`, `PROGRESS.md`, `DECISIONS.md`, MIT `LICENSE`.
- Verify SUMO: `sumo --version`, set `SUMO_HOME`.
- Build `network/toy/` (symmetric 4-way) and run it under TraCI control for 300 s, switching phases from Python.

**Done when:** the toy junction runs headless under TraCI and libsumo, and `pytest -q` runs (even with few tests). Commit.

### Phase 1 — Network and demand (0:40–1:40)

- `network/build_network.py` (Path A if bbox, else Path B; 60-minute cap on Path A).
- `demand/vtypes.add.xml`, `demand/generate.py` for 4 regimes, `counts.csv` (synthetic or user), DR pool of 200 files.
- Webster plans per regime → `network/tls_fixed_<regime>.add.xml`.
- Validation run: fixed-time, peak regime, 3600 s with sub-lane on.

**Done when:** the junction runs for 3600 s with four vehicle classes under fixed-time in every regime; teleports < 1 %; queues are plausible (no permanent gridlock, no empty network at peak). Save a screenshot via `sumo-gui --start --quit-on-end` with `--gui-settings-file` and screenshot option to `docs/network.png`. Commit.

### Phase 2 — Environment, rewards, baselines, budget (1:40–3:00)

- `greenwave/env/signal_env.py`: Gymnasium env, timing state machine (Section 4.2), state builder, reward registry, episode logging, `info` with per-step diagnostics.
- `greenwave/env/rewards.py`: all rewards in Section 4.3.
- Controllers (Section 6).
- Tests: `test_safety.py` (100 random-policy episodes of 600 s: never a green < 10 s, always 3 s yellow on change, never a green > 60 s), `test_rewards.py` (hand-computed cases incl. fairness penalty), `test_webster.py`, `test_max_pressure.py`, `test_env_smoke.py`.
- `experiments/evaluate.py` and `greenwave/metrics.py`; run all baselines × 4 regimes × 10 eval seeds in parallel.
- `experiments/budget.py` → `runs/plan.json`.

**Done when:** all tests pass; `results/summary/baselines.csv` has every baseline in every regime; a profile is chosen and logged. Commit.

### Phase 3 — Agents and sanity checks (3:00–4:00)

- `agents/dqn_scratch.py` (Section 7.1), `agents/train_sb3.py` (Section 7.2), shared training entry point `python -m greenwave.train --config ...`.
- Toy sanity: Double DQN beats random on the toy junction within 20k steps.
- Smoke: 10k steps of each agent on the real junction, peak regime; learning curve logged.
- λ/T sweep launched first in the queue (Section 4.3).

**Done when:** toy sanity passes; smoke runs finish without errors; TensorBoard shows curves. Commit.

**Debug checklist if the agent does not learn:** check reward scale (typical |r| should be 0.1–10), confirm the state is normalised and not constant, lengthen exploration to 70 %, lower lr to 5e-5, verify the target uses `terminated` not `truncated`, verify actions actually change the phase in SUMO.

### Phase 4 — Training queue (starts 4:00, runs in the background ~6–8 h)

- `python experiments/run_queue.py --plan runs/plan.json --workers N` in the background.
- Order: λ/T sweep → regime-matched Double DQN fair (peak first) → DR → SB3 DQN, PPO → ablations.
- **Checkpoint (about 1 h after launch):** the first peak-regime Double DQN run at ~30k steps. Then at full length, the skewed-regime run must beat `fixed_matched` on person-wait. See Section 13 for what to do if not.
- Update `PROGRESS.md` every time a job finishes (status line per job).

**Done when:** all jobs in the plan have `done.flag`, or the cut-scope rule was applied and logged. Commit the summaries (not raw runs).

### Phase 5 — Website build with fixture data (4:00–9:00, in parallel)

- Scaffold `web/` (Section 11.10), design tokens, fonts, layout, header, footer, theme toggle.
- Write zod schemas and `web/fixtures/*.json` (flagged `mock: true`) that match Section 11.2 exactly, including a small synthetic replay generated by a script (not hand-typed).
- Build pages in this order: `/demo` (replay engine first, it is the hardest), `/`, `/results`, `/method`, `/junction`, `/about`.
- `check-data.mjs`, OG image script, sitemap/robots.
- Run Lighthouse locally (`npx lighthouse` against `npx serve out`) and fix to the quality bars.

**Done when:** `npm run lint && npm run typecheck && npm run build` pass with fixtures in dev mode; all pages render at 360 px and 1440 px; arena plays two synced replays at 60 fps. Commit.

### Phase 6 — Evaluation, figures, replays, export (after training, ~1.5 h)

- `experiments/evaluate.py` for all trained agents (best checkpoints) × 4 regimes × 10 eval seeds.
- `experiments/generalisation.py`, `experiments/ablations.py`, Welch t-tests.
- `experiments/figures.py`: every figure in `report/figures/` (PNG 200 dpi + SVG), seaborn style matched to the site palette.
- `experiments/record_replay.py`: the 6 scenes.
- `experiments/export_web.py`: write `web/public/data/` with `mock: false`, git SHA, deviations from `DECISIONS.md`.
- `experiments/make_readme_gif.py`: 8–10 s GIF of the hero scene side by side → `docs/demo.gif` (< 6 MB).

**Done when:** `make eval figures replays export` regenerates everything from saved checkpoints with one command; `CI_REQUIRE_REAL_DATA=1 npm run build` passes. Commit.

### Phase 7 — Local live demo, report material (~1 h)

- `demo/side_by_side.py`: launches two `sumo-gui` windows (traci labels `left`, `right`) with the same route file and seed, left = chosen baseline, right = chosen agent; CLI flags `--scene`, `--left`, `--right`; key/CLI command to **inject a surge** on one approach via `traci.vehicle.add` (30 vehicles over 60 s); writes metrics to a local JSON lines file.
- `demo/dashboard.py`: Streamlit app tailing that file, live waiting-time and queue plots.
- `report/REPORT.md`: abstract, introduction, related work (from reading list), method, setup, results (tables and figures pulled from `results/summary/`), discussion including where max-pressure wins, limitations, future work, references. Every number is filled by a small script (`report/fill.py`) from the summaries, not typed.
- `report/slides.md`: 12-slide outline matching the demo plan.
- `report/viva.md`: Section 16 questions with answers written from this project's actual results, plus the Q-learning update and one Double DQN step to rehearse.

**Done when:** the side-by-side demo runs offline; report numbers match `results/summary/`. Commit.

### Phase 8 — Polish, GitHub, Vercel (~1 h)

- README (Section 15), badges, `docs/demo.gif`, screenshots of the site.
- `.github/workflows/ci.yml`: job 1 (ubuntu, Python 3.11): install requirements, `ruff check`, `pytest -q` using the quick profile and 300 s episodes; job 2 (Node 20): `npm ci`, lint, typecheck, `CI_REQUIRE_REAL_DATA=1 npm run build` in `web/`.
- Final Lighthouse pass. Check every page in light and dark mode.
- If the GitHub CLI is authenticated: `gh repo create greenwave-rl --public --source . --push`. Otherwise print the exact commands for the human.
- Vercel: see Section 15.2.

**Done when:** Section 21 checklist is fully ticked. Final commit and tag `v1.0`.

---

## 13. Checkpoints and cut-scope rules

| When | Check | If it fails |
| --- | --- | --- |
| End of Phase 1 | Network runs, teleports < 1 % | Switch to Path B (plain XML); reduce peak volume by 15 % |
| Phase 3 | Toy sanity passes | Debug checklist (Phase 3). Do not train on the real junction until this passes |
| Phase 4 + 1 h | Peak Double DQN at 30k steps shows a rising eval curve | Lengthen exploration, lower lr, re-check reward scale; restart that job only |
| End of Phase 4 | Some agent beats `fixed_matched` in skewed | Cut scope in this order: (1) drop state and interval ablations, (2) drop SB3 DQN (keep PPO), (3) use synthetic demand only. **Never drop** the fairness reward, the real-junction setting, or the generalisation matrix together with DR |
| End of Phase 4 | Still no agent beats fixed-time | Report it honestly; run the full profile on the skewed regime overnight; the site and report present the negative result with analysis |

If max-pressure wins, report it. "A simple rule matches deep RL on one junction, and here is where RL starts to pay off" is a legitimate finding and a strong viva position.

---

## 14. Final demo plan (8 minutes)

| Time | Segment | Local (`demo/side_by_side.py`) | Website fallback (`/demo`) |
| --- | --- | --- | --- |
| 1 min | The junction | Site photo beside sumo-gui view | `/junction` |
| 2 min | Fixed-time vs RL | Two windows, same traffic, same seed; Streamlit waiting-time plot | Scene "Hero" |
| 1 min | The surge | Inject a burst on one approach; the timer ignores it, the agent reallocates green | Scene "Surge" |
| 2 min | The starvation problem | Agent without fairness term: point at the minor road stuck on red; switch to our reward | Scene "Starvation" |
| 1 min | The bus | Passenger weighting on: the bus approach clears sooner | Scene "Bus" (highlight buses) |
| 1 min | Results | Main table and generalisation grid, including where we lose to max-pressure | `/results` + Scene "Honest" |

SUMO GUI windows can lag on a projector. Test in the room and keep the website (which works offline via `npx serve web/out`) and `docs/demo.gif` as backups.

---

## 15. GitHub and Vercel publishing

### 15.1 README.md structure

1. Title, one-line pitch, badges (CI, license, Python, live site link).
2. `docs/demo.gif`.
3. What it does (3 bullets), key results table (auto-filled from `results/summary/`), "Data: synthetic demand" note if true.
4. Method in brief with the reward formula.
5. Quick start: `make setup && make all` and `make demo`.
6. Reproduce: profiles, expected runtime, hardware used.
7. Repo layout.
8. Website: local dev and deploy.
9. Limitations, future work, citation, license.

### 15.2 Vercel

1. Push the repo to GitHub.
2. On vercel.com: Add New → Project → import `greenwave-rl`.
3. **Root Directory: `web`**. Framework preset: Next.js. Build command: `npm run build`. No env vars required; optionally set `NEXT_PUBLIC_SITE_URL=https://<your-domain>`.
4. Deploy. Every push to `main` redeploys.
5. Custom domain: Project → Settings → Domains.

Keep `web/public/data/` under 30 MB in total (replays dominate; shorten windows if needed).

---

## 16. Viva preparation

| Likely question | What to have ready |
| --- | --- |
| Is your state Markov? | No, strictly: it omits vehicles between detectors and upstream arrivals. Explain partial observability and why it still works. |
| Why a target network and a replay buffer? | Moving targets and correlated samples destabilise Q-learning with function approximation. |
| Why does DQN overestimate, and what does Double DQN change? | The max over noisy estimates is biased upward; Double DQN decouples action selection (online net) from evaluation (target net). |
| Why is your reward not simply negative waiting time? | Credit assignment and scale; the difference form is denser and bounded. |
| Why can max-pressure match your agent? | It is throughput-optimal under idealised assumptions and needs no training. |
| Would this work on the real junction? | Sim-to-real gap: sensing errors, driver behaviour, pedestrians, safety certification. |
| How do you know the agent has converged? | Evaluation-reward plateau across seeds, not the training curve of one run. |
| Why are safety constraints in the env, not the reward? | Hard guarantees; a learned penalty can be traded off, a constraint cannot. |
| Why is episode end truncation, not termination? | Traffic does not stop at 3,600 s; treating it as terminal biases values near the end. |
| Your transitions last 5 s or 13 s. Is constant γ correct? | It is a semi-MDP simplification; the `--smdp-discount` flag tests γ^(Δt/5). |
| Why passenger weights of 40 for a bus? | Stated occupancy assumption; sensitivity test with 20 and 60. |
| Why only one junction? | Scope; corridor multi-agent control is the first extension. |

Rehearse by writing the Q-learning update and one full Double DQN training step on a whiteboard from memory.

---

## 17. Expected results (hypotheses to test, not claims)

- RL beats fixed-time clearly in skewed and surge regimes, and by less at uniform peak load.
- RL roughly matches max-pressure on a single junction. Beating it consistently is not guaranteed.
- Without the fairness term, mean delay looks best and maximum wait looks worst.
- A policy trained on one regime degrades on others; domain randomisation recovers most of the loss at a small cost in peak performance.
- `fixed_peak` (stale plan) is clearly worse than `fixed_matched` outside the peak regime, which supports the motivation.

---

## 18. Risks and how to contain them

- **The agent does not learn.** Start on the toy junction where success is known. Check reward scale, normalise state, lengthen exploration (Phase 3 checklist).
- **Building the network takes too long.** OSM junctions import with wrong lanes and phases. Hard cap of 60 minutes, then plain XML.
- **High variance across seeds.** Report it with std bands. Use multiple seeds from the start.
- **Training does not fit in the day.** The budget planner sizes the run; deviations are logged and shown on the site. Run the `full` profile later for the final submission.
- **The site shows wrong or fake numbers.** Prevented by the data contract, schema validation and the mock-data build guard.
- **Looks like a tutorial.** The real junction, mixed classes, the fairness reward and the generalisation study separate it. Do not drop more than one.

---

## 19. Future extensions and publication paths

- A corridor of 3–5 junctions with coordinated multi-agent control.
- Emergency-vehicle and bus priority as explicit objectives.
- Camera-based state estimation, replacing perfect simulator observations with detector output.
- Pedestrian phases.
- Venues: student or workshop tracks at intelligent-transport and applied-AI conferences. As a prototype, it fits smart-city pilots.

---

## 20. Reading list

| Topic | Source |
| --- | --- |
| RL foundations | Sutton and Barto, *Reinforcement Learning: An Introduction* (chapters 3, 4, 6) |
| DQN | Mnih et al. (2015), Human-Level Control through Deep Reinforcement Learning |
| Double DQN | van Hasselt et al. (2016), Deep Reinforcement Learning with Double Q-Learning |
| PPO | Schulman et al. (2017), Proximal Policy Optimization Algorithms |
| Max-pressure | Varaiya (2013), Max Pressure Control of a Network of Signalized Intersections |
| RL for signals | Wei et al. (2018), IntelliLight; Wei et al. (2019), PressLight |
| Survey | Wei et al. (2019), A Survey on Traffic Signal Control Methods |
| Benchmarks | Ault and Sharon (2021), Reinforcement Learning Benchmarks for Traffic Signal Control |
| Simulator | Lopez et al. (2018), Microscopic Traffic Simulation using SUMO |
| Indian traffic | IRC:106-1990 (PCU values); IRC:SP:41 (junction design) |

Listed from memory; confirm titles, years and IRC values before citing.

---

## 21. Final acceptance checklist

- [ ] `make all` regenerates every result, figure, replay and the web data from saved checkpoints.
- [ ] `pytest` and `ruff` pass; CI is green on GitHub.
- [ ] Safety constraints proven by `test_safety.py` (min green, yellow, max green).
- [ ] Main table: all controllers × 4 regimes × 10 eval seeds, mean ± std, significance marks.
- [ ] Double DQN vs SB3 DQN vs PPO learning curves with seed bands.
- [ ] Both 4 × 4 generalisation grids and the DR row with "gap recovered".
- [ ] Fairness ECDFs for each reward design; starvation visible without the penalty.
- [ ] All ablations in Section 8.4 run (or listed as deviations).
- [ ] Six replay scenes recorded and playable on `/demo`.
- [ ] Website: all six pages, light and dark, 360–1920 px, Lighthouse targets met, no mock data, deviations visible.
- [ ] Local side-by-side SUMO demo with surge injection and Streamlit plots runs offline.
- [ ] `report/REPORT.md`, `slides.md`, `viva.md` complete with numbers from the summaries.
- [ ] README with GIF, results table and live link; repository public; Vercel deployment live.
- [ ] `PROGRESS.md` final; `DECISIONS.md` lists every deviation from this specification.
