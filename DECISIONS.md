# Decisions and deviations

Every choice that departs from, or fills a gap in, `GREENWAVE_BUILD.md`. Entries marked
**[deviation]** are shown on the website's Results page.

## Phase 0 answers (2026-10-09)

- **Junction:** generic 4-arm junction from plain XML (Path B), 3 lanes on the major road
  (E/W) and 2 on the minor road (N/S). The OSM path (Path A) was not attempted. Effect: the
  geometry is representative, not a named real junction.
- **Demand:** no field counts, so demand is synthetic (`meta.synthetic_demand = true`).
- **Machine:** Windows 11, Intel i5-12450H (8 physical cores), 15.6 GB RAM. Training runs
  natively on Windows with 7 workers, not under WSL2.

## Environment and tooling

- **Python 3.11.16** in `.venv`, **SUMO 1.28.0** from the `eclipse-sumo` wheel.
- **GNU make is not installed on this machine.** `tasks.py` implements every Makefile
  target and the Makefile delegates to it; `python tasks.py all` equals `make all`.
- **pyarrow pinned below 24** because libsumo 1.28 is built against Arrow 23 and warns on
  every import otherwise.

## Modelling choices the spec left open

- **Fixed-time and actuated baselines run as native SUMO programs.** The environment has a
  passive mode in which it only observes, so Webster greens are exact to the second instead
  of being rounded to the 5 s decision grid, and "actuated" is SUMO's own controller as the
  spec asks. Metrics come from the same code path as every other controller.
- **Free left turn** is modelled as a permissive green (`g`): left-turners may go during
  other phases but yield to the protected stream.
- **Forced switch at max green** happens inside the same environment step, so a transition
  lasts 5 s (extend), 13 s (switch) or 18 s (extend to 60 s, then forced switch).
- **kappa_q = 10** for the queue and pressure rewards (not fixed by the spec).
- **Webster:** displayed green = effective green + 2 s start-up loss; saturation flow
  525 PCU/h per metre of approach width; surge plan uses time-averaged flows.
- **Training simulations omit tripinfo output and the emissions device.** Neither changes
  vehicle dynamics; evaluation always enables both.
- **Seeds:** training samples SUMO seeds 0-899. Seeds 900-901 select checkpoints, 902-906
  select lambda and T, 1000-1009 are evaluation only. (The spec's 0-999 training range
  overlapped its own validation seeds.)

## Deviations

### 2026-10-09 - Checkpoint selection metric  **[deviation]**
- **What failed:** "checkpoint the best by mean eval reward" does not work for
  difference-form rewards. The undiscounted episode sum of `W(t-1) - W(t)` telescopes to
  `-W(final)`, which depends only on the last second of the episode.
- **Done instead:** checkpoints are selected by the time-averaged potential form of the same
  objective, `-(1 - gamma) * sum_c w_c W_c / kappa - fairness penalty`, which the discounted
  return optimises. Queue and pressure rewards do not telescope and are scored directly.
- **Effect:** learning curves plot this validation score. Rewards used for training are
  exactly those in the spec.

### 2026-10-09 - Job queue implementation
- **What:** `run_queue.py` launches one subprocess per job with a core-aware scheduler
  instead of a `ProcessPoolExecutor`, because libsumo allows one simulation per process and
  PPO needs four cores. Resumability, per-job logs and `status.json` are as specified.
- **Effect:** none on results.

### 2026-10-09 - Ablation references
- **What:** ablations train with the ablation budget, so two reference runs with the same
  budget (`abl_ref__peak`, `abl_ref__skewed`) were added; each ablation is compared with its
  reference, not with the longer main runs. Decision-interval ablations scale their step
  count (0.7x at 10 s, 0.6x at 15 s) so they see a similar amount of simulated time.
- **Effect:** four extra short jobs; ablation comparisons are budget-matched.

### 2026-10-09 - Aggregation over training seeds
- **What:** an RL row in the result tables averages the policies of all training seeds
  for each evaluation seed, then reports mean and standard deviation over the 10 evaluation
  seeds. Welch tests therefore compare 10 values against 10.
- **Effect:** the reported spread is across traffic seeds; spread across training seeds is
  shown separately by the learning-curve bands.
