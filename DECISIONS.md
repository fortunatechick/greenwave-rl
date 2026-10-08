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

### 2026-10-09 - Passenger weights normalised in the reward  **[deviation]**
- **What failed:** the reward-scale check of Phase 3. With raw passenger weights
  (bus = 40) and kappa = 100, a random policy at peak produced |r| of 21 on average and up
  to 150, outside the 0.1-10 range the spec asks for, and the fairness penalty (about 0.6)
  was under 3 % of the reward, so lambda had almost no effect.
- **Done instead:** in the reward, passenger weights are divided by the mean occupancy of
  the traffic mix (4.525 persons per vehicle). Relative weights are unchanged (a bus still
  counts 20 times a car); the passenger-weighted reward now has the scale of the
  vehicle-count reward. Equivalent to kappa = 452.5 for the passenger-weighted terms.
- **Effect:** lambda means the same thing with vehicle and passenger weighting, so that
  ablation compares weighting and not scale. Reported person-weighted metrics are ratios
  and are not affected.

### 2026-10-09 - Discount 0.95 and reward clipping  **[deviation]**
- **What failed:** the Phase 4 checkpoint. With gamma = 0.99, Double DQN on the skewed regime reached an average
  queue of about 12.5 vehicles by 10k steps (max-pressure: 16.3) and then collapsed to about 65 by 20k, in most of
  the first sweep runs. Seven 30k-step variants were run on one seed: lower learning rate with longer exploration
  (never got below 19.5), target update every 2000 steps (collapsed to 62), Polyak averaging (never learned),
  learning-rate decay (collapsed mid-run), reward clipping to +-3 (one dip to 23.8, otherwise 12-14),
  gamma = 0.95 (11.3-13.6 from 10k steps on, no collapse).
- **Done instead:** every agent (Double DQN, SB3 DQN, PPO) trains with gamma = 0.95 instead of 0.99 and with rewards clipped to [-3, 3] during training. Both shrink the range of Q-values, which grows with accumulated waiting in congested states. Evaluation metrics are unaffected by clipping.
- **Effect:** the effective planning horizon drops from about 100 to about 20 decisions. The choice rests on one
  seed per variant, and the combination of the two changes was not itself tested before the long runs.

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
