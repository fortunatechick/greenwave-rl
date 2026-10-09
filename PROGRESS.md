# Progress

**Current phase:** 8 (delivered locally; Vercel deployment open)  
**Last update:** 2026-10-09 07:10

| Phase | Status | Notes |
| --- | --- | --- |
| 0 Setup and toy junction | done | Python 3.11.16, SUMO 1.28.0, toy runs under TraCI and libsumo |
| 1 Network and demand | done | Plain-XML junction, 4 regimes, 200-file DR pool, Webster plans, 0 % teleports |
| 2 Env, rewards, baselines, budget | done | Baselines x 4 regimes x 10 seeds; day profile chosen |
| 3 Agents and sanity checks | done | Toy sanity passed (Double DQN 52 s vs random 131 s) |
| 4 Training queue | done | 58 jobs, 0 failed, 26.7 CPU-hours (02:01-06:35), after a restart for stability |
| 5 Website | done | 6 pages, replay arena, real data, mock guard passes |
| 6 Evaluation, figures, replays, export | done | `python tasks.py eval figures replays export` |
| 7 Local demo and report | done | Side-by-side demo run for 120 s with a scripted surge; Streamlit dashboard not run |
| 8 Polish, GitHub, Vercel | partly | Private repo `fortunatechick/greenwave-rl`; Vercel not deployed; CI not yet observed |

## Key numbers (10 held-out seeds, wait per person in seconds)

| Controller | Low | Peak | Skewed | Surge |
| --- | --- | --- | --- | --- |
| Fixed-time (matched) | 12.1 | 34.2 | 25.7 | 36.4 |
| Max-pressure | 9.1 | 16.3 | 17.8 | 17.6 |
| Double DQN, fair (regime-matched) | 9.3 | 21.3 | 17.7 | 14.9 |
| Double DQN, fair + DR | 14.5 | 28.5 | 14.7 | 18.1 |

- Against max-pressure the regime-matched agent is statistically tied in all four regimes.
- Fairness penalty: longest wait 115 s against 174 s without it (p = 0.029), at a cost of 15.7 s against 12.9 s
  wait per person.
- Passenger weighting: bus delay 29.3 s against 37.8 s, not statistically significant (p = 0.17).
- Domain randomisation recovers 55 % of the generalisation gap on wait per person.
- Chosen lambda = 4, T = 90 s.

## Open issues

- Vercel deployment and a public repository are not done (repository is private at the user's request).
- GitHub Actions CI has been written but its first run has not been checked.
- Lighthouse was measured on the home page only (93 / 100 / 100 / 100, mobile).
- DQN training still shows occasional bad checkpoints; results use the best checkpoint per run.
- Not run: the `full` profile, the corridor stretch goal, the Streamlit dashboard, a from-scratch `make all`.

## Training queue

<!-- queue:start -->
Finished: 58 of 58 jobs done. Per-job detail in `results/summary/training_status.json`.
<!-- queue:end -->
