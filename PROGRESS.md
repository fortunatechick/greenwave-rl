# Progress

**Current phase:** 4 (training) with 5-8 scaffolding complete  
**Last update:** 2026-10-09 01:40

| Phase | Status | Notes |
| --- | --- | --- |
| 0 Setup and toy junction | done | Python 3.11.16, SUMO 1.28.0, toy runs under TraCI and libsumo |
| 1 Network and demand | done | Plain-XML junction, 4 regimes, 200-file DR pool, Webster plans, 0 % teleports |
| 2 Env, rewards, baselines, budget | done | 30 tests green; baselines x 4 regimes x 10 seeds in `results/summary/baselines.csv`; day profile chosen |
| 3 Agents and sanity checks | done | Toy sanity passed (Double DQN 52 s vs random 131 s); all three agents smoke-tested |
| 4 Training queue | in progress | First launch stopped after the sweep exposed a DQN instability; diagnostics running |
| 5 Website | done on fixtures | 6 pages, replay engine, lint / typecheck / build pass with mock data |
| 6 Evaluation, figures, replays, export | scripts ready | Waiting for trained agents |
| 7 Local demo and report | scripts ready | `demo/side_by_side.py`, `demo/dashboard.py`, `report/fill.py` |
| 8 Polish, GitHub, Vercel | pending | README and CI written; publishing needs the user's go-ahead |

## Key numbers

- Peak demand: 3,636 veh/h, Webster cycle 120 s, design degree of saturation 0.85.
- Baselines, wait per person at peak: fixed-time 34.2 s, actuated 23.0 s, max-pressure 16.3 s, random 60.9 s.
- Simulation speed: about 55 decisions/s per process when idle, about 25/s with 7 jobs in parallel.

## Open issues

- **DQN instability.** In the first sweep, policies reached an average queue of about 12.5 vehicles on the skewed
  regime by 10k steps (max-pressure: 16.3) and then collapsed to about 65 by 20k. Seven 30k-step variants
  (learning rate, target update, discount, reward clipping, Polyak averaging, learning-rate decay) are running to
  pick a stabiliser before the long runs start. Best-checkpoint selection already protects the final numbers, but
  the cause should be fixed rather than hidden.

## Training queue

<!-- queue:start -->
Stopped at 01:30 for the stability diagnostics. To be relaunched.
<!-- queue:end -->
